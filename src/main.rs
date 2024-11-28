use actix_web::{web, App, HttpServer, Responder, HttpResponse, middleware::Logger};
use dotenv::dotenv;
use serde::{Deserialize, Serialize};
use reqwest::Client;
use std::env;
use log::{info, error, warn};
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
    HttpResponse::Ok().body("Server is running")
}

async fn add_restaurant(
    body: actix_web::web::Bytes,
    client: web::Data<Client>,
) -> impl Responder {
    let request_id = chrono::Utc::now().format("%Y%m%d%H%M%S%f").to_string();
    info!("Processing restaurant: {}", String::from_utf8_lossy(&body));

    // Try to parse the request body
    let req = match serde_json::from_slice::<AddRestaurantRequest>(&body) {
        Ok(req) => req,
        Err(e) => {
            let error_msg = format!("Invalid request format: {}", e);
            error!("{}", error_msg);
            return HttpResponse::BadRequest().body(error_msg);
        }
    };

    let sanitized_url = match utils::validate_and_sanitize_url(&req.url) {
        Ok(url) => url,
        Err(e) => {
            error!("URL validation failed: {}", e);
            return HttpResponse::BadRequest().body(e);
        }
    };

    info!("Getting place details for: {}", sanitized_url);

    let place_details = match google_places::get_place_details(&client, &sanitized_url).await {
        Ok(details) => details,
        Err(e) => {
            error!("Error getting place details: {}", e);
            return HttpResponse::InternalServerError().body(format!("Failed to get place details: {}", e));
        }
    };

    let cover_url = match cloudinary::upload_image(&client, &place_details.photo_reference).await {
        Ok(url) => {
            info!("Updating {} - Cover Image: Updated", place_details.name);
            Some(url)
        },
        Err(e) => {
            warn!("Failed to upload image for {}: {}", place_details.name, e);
            None
        }
    };

    let cuisine_type = match yelp::get_cuisine_type(&client, &place_details.name, &place_details.city).await {
        Ok(cuisine) => {
            info!("Updating {} - Cuisine Type: {}", place_details.name, cuisine);
            cuisine
        },
        Err(e) => {
            warn!("Failed to get cuisine type for {}: {}", place_details.name, e);
            "❓".to_string()
        }
    };

    let restaurant_details = RestaurantDetails {
        name: place_details.name.clone(),
        website: place_details.website.clone(),
        price_level: place_details.price_level.clone(),
        city: place_details.city.clone(),
        country: place_details.country.clone(),
        google_maps_link: place_details.google_maps_link.clone(),
        address: place_details.address.clone(),
        cuisine_type: cuisine_type.clone(),
        photo_reference: place_details.photo_reference.clone(),
    };

    // Log all the details
    info!("Updating {} - name: {}", place_details.name, restaurant_details.name);
    info!("Updating {} - website: {}", place_details.name, restaurant_details.website);
    info!("Updating {} - price_level: {}", place_details.name, restaurant_details.price_level);
    info!("Updating {} - city: {}", place_details.name, restaurant_details.city);
    info!("Updating {} - country: {}", place_details.name, restaurant_details.country);
    info!("Updating {} - google_maps_link: {}", place_details.name, restaurant_details.google_maps_link);
    info!("Updating {} - address: {}", place_details.name, restaurant_details.address);
    info!("Updating {} - cuisine_type: {}", place_details.name, restaurant_details.cuisine_type);

    match notion::create_or_update_entry(&client, restaurant_details, cover_url).await {
        Ok(message) => {
            info!("{}", message);
            HttpResponse::Ok().body(message)
        },
        Err(e) => {
            error!("Error adding restaurant to Notion: {}", e);
            HttpResponse::InternalServerError().body(e)
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

    logging::log_start_message();
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
    .bind("0.0.0.0:3754")?
    .run()
    .await
}