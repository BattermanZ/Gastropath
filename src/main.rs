use actix_web::{web, App, HttpServer, Responder, HttpResponse, middleware::Logger};
use dotenv::dotenv;
use serde::{Deserialize, Serialize};
use reqwest::Client;
use std::env;
use log::{info, error, debug, warn};
use actix_governor::{Governor, GovernorConfigBuilder};

mod google_places;
mod yelp;
mod notion;
mod cloudinary;
mod utils;
mod logging;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
struct AddRestaurantRequest {
    #[serde(alias = "URL")]
    url: String,
}

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
    expected_format: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct RestaurantDetails {
    name: String,
    website: String,
    price_level: String,
    city: String,
    country: String,
    google_maps_link: String,
    address: String,
    cuisine_type: String,
    photo_reference: Option<String>,
}

async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "message": "Server is running"
    }))
}

async fn add_restaurant(
    body: actix_web::web::Bytes,
    client: web::Data<Client>,
) -> impl Responder {
    let request_id = chrono::Utc::now().format("%Y%m%d%H%M%S%f").to_string();
    info!("Request {}: Add restaurant request received", request_id);
    
    // Log raw request body for debugging
    let body_str = String::from_utf8_lossy(&body);
    debug!("Request {}: Raw request body: {}", request_id, body_str);

    // Try to parse the request body
    let req = match serde_json::from_slice::<AddRestaurantRequest>(&body) {
        Ok(req) => req,
        Err(e) => {
            let error_msg = format!("Invalid request format: {}", e);
            error!("Request {}: {}", request_id, error_msg);
            
            // Return a helpful error response with expected format
            let expected_format = serde_json::json!({
                "url": "https://maps.app.goo.gl/example"
            });
            
            return HttpResponse::BadRequest().json(ErrorResponse {
                error: error_msg,
                expected_format,
            });
        }
    };

    debug!("Request {}: Received URL: {}", request_id, req.url);
    debug!("Request {}: Parsed request body: {:?}", request_id, req);

    let sanitized_url = match utils::validate_and_sanitize_url(&req.url) {
        Ok(url) => url,
        Err(e) => {
            error!("Request {}: URL validation failed: {}", request_id, e);
            return HttpResponse::BadRequest().json(ErrorResponse {
                error: e,
                expected_format: serde_json::json!({
                    "url": "https://maps.app.goo.gl/example"
                }),
            });
        }
    };

    info!("Request {}: Sanitized URL: {}", request_id, sanitized_url);

    let place_details = match google_places::get_place_details(&client, &sanitized_url).await {
        Ok(details) => details,
        Err(e) => {
            error!("Request {}: Error getting place details: {}", request_id, e);
            return HttpResponse::InternalServerError().json(ErrorResponse {
                error: format!("Failed to get place details: {}", e),
                expected_format: serde_json::json!({
                    "url": "https://maps.app.goo.gl/example"
                }),
            });
        }
    };

    debug!("Request {}: Place details: {:?}", request_id, place_details);

    let cover_url = match cloudinary::upload_image(&client, &place_details.photo_reference).await {
        Ok(url) => Some(url),
        Err(e) => {
            warn!("Request {}: Failed to upload image: {}", request_id, e);
            None
        }
    };

    let cuisine_type = match yelp::get_cuisine_type(&client, &place_details.name, &place_details.city).await {
        Ok(cuisine) => cuisine,
        Err(e) => {
            warn!("Request {}: Failed to get cuisine type: {}", request_id, e);
            "❓".to_string()
        }
    };

    let restaurant_details = RestaurantDetails {
        name: place_details.name,
        website: place_details.website,
        price_level: place_details.price_level,
        city: place_details.city,
        country: place_details.country,
        google_maps_link: place_details.google_maps_link,
        address: place_details.address,
        cuisine_type,
        photo_reference: place_details.photo_reference,
    };

    match notion::create_or_update_entry(&client, restaurant_details.clone(), cover_url).await {
        Ok(_) => {
            info!("Request {}: Restaurant added successfully", request_id);
            HttpResponse::Ok().json(serde_json::json!({
                "status": "success",
                "message": "Restaurant added successfully"
            }))
        },
        Err(e) => {
            error!("Request {}: Error adding restaurant: {}", request_id, e);
            HttpResponse::InternalServerError().json(ErrorResponse {
                error: format!("Failed to add restaurant to Notion: {}", e),
                expected_format: serde_json::json!({
                    "url": "https://maps.app.goo.gl/example"
                }),
            })
        }
    }
}

fn log_environment_variables() {
    let mut env_vars = std::collections::HashMap::new();
    for (key, value) in env::vars() {
        if key == "API_KEY" {
            env_vars.insert(key, utils::mask_api_key(&value));
        } else if key.to_uppercase().contains("KEY") {
            env_vars.insert(key, "*".repeat(8));
        } else {
            env_vars.insert(key, value);
        }
    }
    info!("Environment variables: {}", serde_json::to_string_pretty(&env_vars).unwrap());
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    dotenv().ok();
    
    // Setup logging
    if let Err(e) = logging::setup_logging() {
        eprintln!("Failed to set up logging: {}", e);
        return Ok(());
    }

    log_environment_variables();

    let client = Client::new();

    info!("Starting Gastropath server");

    HttpServer::new(move || {
        let governor_config = GovernorConfigBuilder::default()
            .per_second(5)
            .burst_size(10)
            .finish()
            .unwrap();

        App::new()
            .wrap(Logger::default())
            .wrap(Governor::new(&governor_config))
            .app_data(web::Data::new(client.clone()))
            .route("/health", web::get().to(health_check))
            .route("/add_restaurant", web::post().to(add_restaurant))
    })
    .bind("0.0.0.0:9999")?
    .run()
    .await
}

