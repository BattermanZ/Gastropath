use reqwest::Client;
use serde_json::{json, Value};
use std::env;
use log::{info, error, debug};
use crate::RestaurantDetails;

pub async fn create_or_update_entry(
    client: &Client,
    details: RestaurantDetails,
    cover_url: Option<String>,
) -> Result<(), Box<dyn std::error::Error>> {
    info!("Creating or updating Notion entry for: {}", details.name);
    let api_key = env::var("NOTION_API_KEY")?;
    let database_id = env::var("NOTION_DATABASE_ID")?;

    let existing_entry = find_existing_entry(client, &api_key, &database_id, &details.name).await?;

    let url = "https://api.notion.com/v1/pages".to_string();

    debug!("Notion API request URL: {}", url);

    debug!("Notion API Key (first 4 chars): {}", &api_key[..4]);
    debug!("Notion Database ID: {}", database_id);
    debug!("Notion API Version: 2022-06-28");
    debug!("Request URL: {}", url);

    debug!("Notion API request URL: {}", url);

    let mut data = json!({
        "properties": {
            "City": {
                "rich_text": [{"text": {"content": details.city}}]
            },
            "Country": {
                "rich_text": [{"text": {"content": details.country}}]
            },
            "Cuisine Type": {
                "rich_text": [{"text": {"content": details.cuisine_type}}]
            },
            "Google Maps": {
                "url": details.google_maps_link
            },
            "Price range": {
                "select": {"name": details.price_level}
            },
            "Website": {
                "url": details.website
            },
            "Name": {
                "title": [{"text": {"content": details.name}}]
            }
        }
    });

    if existing_entry.is_none() {
        data["parent"] = json!({"database_id": database_id});
        data["icon"] = json!({"type": "emoji", "emoji": "🍽️"});
    }

    if let Some(url) = cover_url {
        data["cover"] = json!({"type": "external", "external": {"url": url}});
    }

    debug!("Notion API request data: {:?}", data);

    debug!("Sending request to Notion API");
    debug!("Headers: Authorization: Bearer <redacted>, Notion-Version: {}", "2022-06-28");
    debug!("Request body: {}", serde_json::to_string_pretty(&data).unwrap());

    let response = client.post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Notion-Version", "2022-06-28")
        .json(&data)
        .send()
        .await?;

    if response.status().is_success() {
        info!("Successfully {} {} in Notion", if existing_entry.is_some() { "updated" } else { "created" }, details.name);
        Ok(())
    } else {
        let status = response.status();
        let headers = response.headers().clone();
        let error_body = response.text().await?;
        error!("Failed to update Notion. Status: {}", status);
        error!("Response headers: {:?}", headers);
        error!("Error body: {}", error_body);
        Err(format!("Failed to create Notion entry: {} - {}", status, error_body).into())
    }
}

async fn find_existing_entry(
    client: &Client,
    api_key: &str,
    database_id: &str,
    restaurant_name: &str,
) -> Result<Option<String>, Box<dyn std::error::Error>> {
    let url = format!("https://api.notion.com/v1/databases/{}/query", database_id);
    debug!("Querying Notion database: {}", url);

    let query = json!({
        "filter": {
            "property": "Name",
            "title": {
                "equals": restaurant_name
            }
        }
    });

    let response = client.post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Notion-Version", "2022-06-28")
        .json(&query)
        .send()
        .await?
        .json::<Value>()
        .await?;

    debug!("Notion query response: {:?}", response);

    if let Some(results) = response["results"].as_array() {
        if let Some(first_result) = results.first() {
            return Ok(first_result["id"].as_str().map(String::from));
        }
    }

    Ok(None)
}

