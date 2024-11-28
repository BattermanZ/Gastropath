use url::Url;
use log::{info, debug, error};

pub fn validate_and_sanitize_url(url: &str) -> Result<String, String> {
    debug!("Validating and sanitizing URL: {}", url);

    if url.len() > 2000 {
        error!("URL exceeds maximum length");
        return Err("URL exceeds maximum length".to_string());
    }

    let parsed_url = Url::parse(url).map_err(|e| {
        error!("Invalid URL format: {}", e);
        "Invalid URL format".to_string()
    })?;

    if parsed_url.host_str() != Some("maps.app.goo.gl") {
        error!("URL is not from a trusted domain");
        return Err("URL is not from a trusted domain".to_string());
    }

    if !parsed_url.path().starts_with('/') || parsed_url.path().len() < 2 {
        error!("Invalid URL path");
        return Err("Invalid URL path".to_string());
    }

    let allowed_params = ["g_st"];
    let sanitized_query: Vec<(String, String)> = parsed_url
        .query_pairs()
        .filter(|(key, _)| allowed_params.contains(&key.as_ref()))
        .map(|(k, v)| (k.into_owned(), v.into_owned()))
        .collect();

    let mut sanitized_url = format!("https://{}{}", parsed_url.host_str().unwrap(), parsed_url.path());
    if !sanitized_query.is_empty() {
        sanitized_url.push('?');
        sanitized_url.push_str(&url::form_urlencoded::Serializer::new(String::new())
            .extend_pairs(sanitized_query)
            .finish());
    }

    debug!("Sanitized URL: {}", sanitized_url);
    Ok(sanitized_url)
}

pub fn mask_api_key(key: &str) -> String {
    if key.len() > 5 {
        format!("{}{}",
            &key[..5],
            "*".repeat(key.len() - 5)
        )
    } else {
        key.to_string()
    }
}

pub async fn expand_short_url(short_url: &str) -> Result<String, Box<dyn std::error::Error>> {
    debug!("Expanding short URL: {}", short_url);
    let client = reqwest::Client::new();
    let response = client.get(short_url).send().await?;
    let expanded_url = response.url().to_string();
    info!("Expanded URL: {}", expanded_url);
    Ok(expanded_url)
}

