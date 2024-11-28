use log4rs::{
    append::{
        console::ConsoleAppender,
        file::FileAppender,
    },
    config::{Appender, Config, Root},
    encode::pattern::PatternEncoder,
};
use log::{info, LevelFilter};
use std::fs;

pub fn setup_logging() -> Result<(), Box<dyn std::error::Error>> {
    // Create logs directory if it doesn't exist
    fs::create_dir_all("logs")?;

    let log_pattern = "{d(%Y-%m-%d %H:%M:%S)} - {l} - {m}{n}";

    // Create a stdout appender
    let stdout = ConsoleAppender::builder()
        .encoder(Box::new(PatternEncoder::new(log_pattern)))
        .build();

    // Create a file appender
    let file = FileAppender::builder()
        .encoder(Box::new(PatternEncoder::new(log_pattern)))
        .build("logs/gastropath.log")?;

    // Build the log4rs configuration
    let config = Config::builder()
        .appender(Appender::builder().build("stdout", Box::new(stdout)))
        .appender(Appender::builder().build("file", Box::new(file)))
        .build(
            Root::builder()
                .appender("stdout")
                .appender("file")
                .build(LevelFilter::Info),
        )?;

    // Initialize the logger
    log4rs::init_config(config)?;

    Ok(())
}

pub fn log_start_message() {
    info!("==================================================");
    info!("New Gastropath run started");
    info!("==================================================");
}

