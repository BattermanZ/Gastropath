# Build stage
FROM rust:1.82.0-slim-bookworm as builder

# Set the working directory in the container
WORKDIR /usr/src/gastropath

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the Cargo.toml and Cargo.lock files
COPY Cargo.toml Cargo.lock ./

# Copy the source code
COPY src ./src

# Build the application
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Set the working directory in the container
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the built executable from the builder stage
COPY --from=builder /usr/src/gastropath/target/release/gastropath /app/gastropath

# Expose port 3754
EXPOSE 3754

# Command to run the executable
CMD ["./gastropath"]