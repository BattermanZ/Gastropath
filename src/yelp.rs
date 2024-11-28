use reqwest::Client;
use serde_json::Value;
use std::env;
use log::{info, debug, warn};

pub async fn get_cuisine_type(client: &Client, restaurant_name: &str, city: &str) -> Result<String, Box<dyn std::error::Error>> {
    info!("Getting cuisine type for {} in {}", restaurant_name, city);
    let api_key = env::var("YELP_API_KEY")?;
    let url = "https://api.yelp.com/v3/businesses/search";
    
    let params = [
        ("term", restaurant_name),
        ("location", city),
        ("limit", "1"),
    ];

    debug!("Sending request to Yelp API with params: {:?}", params);

    let response = client.get(url)
        .query(&params)
        .header("Authorization", format!("Bearer {}", api_key))
        .send()
        .await?
        .json::<Value>()
        .await?;

    debug!("Received response from Yelp API: {:?}", response);

    if let Some(error) = response.get("error") {
        let error_description = error["description"].as_str().unwrap_or("Unknown error");
        warn!("Yelp API error: {}", error_description);
        return Ok("❓".to_string());
    }

    if let Some(businesses) = response["businesses"].as_array() {
        if let Some(business) = businesses.first() {
            if let Some(categories) = business["categories"].as_array() {
                let cuisine_types: Vec<String> = categories
                    .iter()
                    .filter_map(|category| category["title"].as_str().map(String::from))
                    .collect();
                info!("Found cuisine types: {:?}", cuisine_types);
                return Ok(cuisine_types.join(", "));
            }
        }
    }

    warn!("No cuisine type found for {} in {}", restaurant_name, city);
    Ok("❓".to_string())
}

