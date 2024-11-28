use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::env;
use log::{info, error, debug};

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct PlaceDetails {
    pub name: String,
    pub website: String,
    pub price_level: String,
    pub city: String,
    pub country: String,
    pub google_maps_link: String,
    pub address: String,
    pub photo_reference: Option<String>,
}

pub async fn get_place_details(client: &Client, identifier: &str) -> Result<PlaceDetails, Box<dyn std::error::Error>> {
    info!("Getting place details for: {}", identifier);
    let api_key = env::var("GOOGLE_API_KEY")?;
    let (ftid, query) = if identifier.starts_with("http") {
        let expanded_url = crate::utils::expand_short_url(identifier).await?;
        extract_place_info(&expanded_url)?
    } else {
        (None, identifier.to_string())
    };

    debug!("Extracted ID: {:?}, Query: {}", ftid, query);

    let details = if let Some(id) = ftid {
        match get_details_by_ftid(client, &api_key, id).await {
            Ok(details) => details,
            Err(e) => {
                error!("Error getting place details by FTID: {:?}", e);
                return Err(e);
            }
        }
    } else {
        match get_details_by_query(client, &api_key, query).await {
            Ok(details) => details,
            Err(e) => {
                error!("Error getting place details by query: {:?}", e);
                return Err(e);
            }
        }
    };

    if details.name == "Unknown" {
        error!("Failed to retrieve place details: Unknown place");
        return Err("Place details not found: Unknown place".into());
    }

    debug!("Retrieved place details: {:?}", details);
    Ok(details)
}

fn extract_place_info(url: &str) -> Result<(Option<String>, String), Box<dyn std::error::Error>> {
    let parsed_url = url::Url::parse(url)?;
    let query_params: std::collections::HashMap<_, _> = parsed_url.query_pairs().into_owned().collect();

    let id = query_params.get("ftid")
        .or_else(|| query_params.get("place_id"))
        .cloned();

    let query = query_params.get("q")
        .cloned()
        .unwrap_or_else(|| url.to_string());

    debug!("Extracted parameters - id: {:?}, query: {}", id, query);
    Ok((id, query))
}

async fn get_details_by_ftid(client: &Client, api_key: &str, ftid: String) -> Result<PlaceDetails, Box<dyn std::error::Error>> {
    let url = format!(
        "https://maps.googleapis.com/maps/api/place/details/json?ftid={}&fields=name,formatted_address,website,price_level,address_component,photos,url&key={}",
        ftid, api_key
    );
    debug!("Requesting place details with URL: {}", url);
    let response = client.get(&url).send().await?.json::<serde_json::Value>().await?;
    if let Some(error_message) = response["error_message"].as_str() {
        error!("Google Places API error: {}. Full response: {:?}", error_message, response);
        return Err(format!("Google Places API error: {}. Full response: {:?}", error_message, response).into());
    }
    process_place_details(&response["result"])
}

async fn get_details_by_query(client: &Client, api_key: &str, query: String) -> Result<PlaceDetails, Box<dyn std::error::Error>> {
    let find_place_url = format!(
        "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={}&inputtype=textquery&fields=place_id&key={}",
        query, api_key
    );

    let find_place_response = client.get(&find_place_url).send().await?.json::<serde_json::Value>().await?;
    if let Some(error_message) = find_place_response["error_message"].as_str() {
        error!("Google Places API error: {}", error_message);
        return Err(format!("Google Places API error: {}", error_message).into());
    }
    let place_id = find_place_response["candidates"][0]["place_id"].as_str().ok_or("No place_id found")?;

    let details_url = format!(
        "https://maps.googleapis.com/maps/api/place/details/json?place_id={}&fields=name,formatted_address,website,price_level,address_component,photos,url&key={}",
        place_id, api_key
    );

    let response = client.get(&details_url).send().await?.json::<serde_json::Value>().await?;
    if let Some(error_message) = response["error_message"].as_str() {
        error!("Google Places API error: {}", error_message);
        return Err(format!("Google Places API error: {}", error_message).into());
    }
    process_place_details(&response["result"])
}

fn process_place_details(details: &serde_json::Value) -> Result<PlaceDetails, Box<dyn std::error::Error>> {
    let name = details["name"].as_str().unwrap_or("Unknown").to_string();
    let website = details["website"].as_str().unwrap_or("No website available").to_string();
    let price_level = match details["price_level"].as_i64() {
        Some(level) => "💵".repeat(level as usize),
        None => "❓".to_string(),
    };
    let address = details["formatted_address"].as_str().unwrap_or("No address available").to_string();
    let google_maps_link = details["url"].as_str().unwrap_or("No link available").to_string();

    let mut city = "No city available".to_string();
    let mut country = "No country available".to_string();
    if let Some(components) = details["address_components"].as_array() {
        for component in components {
            if let Some(types) = component["types"].as_array() {
                if types.contains(&serde_json::json!("locality")) {
                    city = component["long_name"].as_str().unwrap_or(&city).to_string();
                }
                if types.contains(&serde_json::json!("country")) {
                    country = component["long_name"].as_str().unwrap_or(&country).to_string();
                }
            }
        }
    }

    let photo_reference = details["photos"][0]["photo_reference"].as_str().map(String::from);

    Ok(PlaceDetails {
        name,
        website,
        price_level,
        city,
        country,
        google_maps_link,
        address,
        photo_reference,
    })
}

