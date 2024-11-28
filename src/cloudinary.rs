use reqwest::Client;
use serde_json::Value;
use std::env;
use log::{info, error, debug};
use sha1::{Sha1, Digest};

lazy_static::lazy_static! {
    static ref CLOUDINARY_CONFIG: CloudinaryConfig = CloudinaryConfig::new();
}

struct CloudinaryConfig {
    cloud_name: String,
    api_key: String,
    api_secret: String,
}

impl CloudinaryConfig {
    fn new() -> Self {
        Self {
            cloud_name: env::var("CLOUDINARY_CLOUD_NAME").expect("CLOUDINARY_CLOUD_NAME must be set"),
            api_key: env::var("CLOUDINARY_API_KEY").expect("CLOUDINARY_API_KEY must be set"),
            api_secret: env::var("CLOUDINARY_API_SECRET").expect("CLOUDINARY_API_SECRET must be set"),
        }
    }
}

pub async fn upload_image(client: &Client, photo_reference: &Option<String>) -> Result<String, Box<dyn std::error::Error>> {
    if let Some(reference) = photo_reference {
        info!("Uploading image to Cloudinary");
        let google_api_key = env::var("GOOGLE_API_KEY")?;

        let photo_url = format!(
            "https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={}&key={}",
            reference, google_api_key
        );

        debug!("Generated photo URL: {}", photo_url);

        let timestamp = chrono::Utc::now().timestamp();
        let signature_string = format!("timestamp={}{}", timestamp, CLOUDINARY_CONFIG.api_secret);
        let signature = Sha1::digest(signature_string.as_bytes());
        let signature = format!("{:x}", signature);

        let form = reqwest::multipart::Form::new()
            .text("file", photo_url)
            .text("api_key", CLOUDINARY_CONFIG.api_key.clone())
            .text("timestamp", timestamp.to_string())
            .text("signature", signature);

        let upload_url = format!(
            "https://api.cloudinary.com/v1_1/{}/image/upload",
            CLOUDINARY_CONFIG.cloud_name
        );

        debug!("Sending request to Cloudinary API: {}", upload_url);

        let response = client.post(&upload_url)
            .multipart(form)
            .send()
            .await?
            .json::<Value>()
            .await?;

        debug!("Received response from Cloudinary: {:?}", response);

        if let Some(secure_url) = response["secure_url"].as_str() {
            info!("Successfully uploaded image to Cloudinary");
            Ok(secure_url.to_string())
        } else {
            let error_message = "Failed to upload image to Cloudinary";
            error!("{}", error_message);
            Err(error_message.into())
        }
    } else {
        let error_message = "No photo reference provided";
        error!("{}", error_message);
        Err(error_message.into())
    }
}

