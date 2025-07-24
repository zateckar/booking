#!/bin/bash

# Booking Application Deployment Script
# This script helps deploy the booking application using Docker

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="booking"
IMAGE_NAME="booking-app"
CONTAINER_NAME="booking-app"
NETWORK_NAME="booking-network"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is installed and running
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    print_success "Docker is installed and running"
}

# Function to check if Docker Compose is available
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        print_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    print_success "Docker Compose is available: $DOCKER_COMPOSE_CMD"
}

# Function to create .env file if it doesn't exist
setup_env_file() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        print_warning "No .env file found. Creating one from .env.example..."
        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            print_warning "Please edit .env file with your actual configuration before continuing."
            read -p "Press Enter to continue after editing .env file..."
        else
            print_error ".env.example file not found. Cannot create .env file."
            exit 1
        fi
    else
        print_success ".env file exists"
    fi
}

# Function to build the Docker image
build_image() {
    print_status "Building Docker image..."
    
    cd "$SCRIPT_DIR"
    docker build -t "$IMAGE_NAME" .
    
    print_success "Docker image built successfully"
}

# Function to stop and remove existing containers
cleanup_existing() {
    print_status "Cleaning up existing containers..."
    
    # Stop and remove container if it exists
    if docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_status "Stopping existing container..."
        docker stop "$CONTAINER_NAME" || true
        docker rm "$CONTAINER_NAME" || true
    fi
    
    print_success "Cleanup completed"
}

# Function to deploy using Docker Compose
deploy_compose() {
    print_status "Deploying using Docker Compose..."
    
    cd "$SCRIPT_DIR"
    
    # Stop existing services
    $DOCKER_COMPOSE_CMD down
    
    # Build and start services
    $DOCKER_COMPOSE_CMD up -d --build
    
    print_success "Application deployed using Docker Compose"
}

# Function to deploy using plain Docker
deploy_docker() {
    print_status "Deploying using plain Docker..."
    
    # Create network if it doesn't exist
    if ! docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
        print_status "Creating Docker network..."
        docker network create "$NETWORK_NAME"
    fi
    
    # Create volumes if they don't exist
    print_status "Creating Docker volumes..."
    docker volume create "${PROJECT_NAME}_data" || true
    docker volume create "${PROJECT_NAME}_logs" || true
    
    # Run the container
    print_status "Starting container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        --network "$NETWORK_NAME" \
        -p 8000:8000 \
        -v "${PROJECT_NAME}_data:/app/data" \
        -v "${PROJECT_NAME}_logs:/app/logs" \
        --env-file "$SCRIPT_DIR/.env" \
        --restart unless-stopped \
        "$IMAGE_NAME"
    
    print_success "Application deployed using Docker"
}

# Function to check application health
check_health() {
    print_status "Checking application health..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/api/oidc/providers &> /dev/null; then
            print_success "Application is healthy and responding"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts - waiting for application to start..."
        sleep 2
        ((attempt++))
    done
    
    print_error "Application failed to start or is not responding"
    return 1
}

# Function to show deployment status
show_status() {
    echo
    echo "=================================================="
    echo "         BOOKING APPLICATION DEPLOYMENT          "
    echo "=================================================="
    echo
    
    if [ "$1" = "compose" ]; then
        print_status "Container status (Docker Compose):"
        $DOCKER_COMPOSE_CMD ps
    else
        print_status "Container status:"
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    fi
    
    echo
    print_success "🎉 Deployment completed successfully!"
    echo
    echo "📱 Main Application: http://localhost:8000"
    echo "🔧 Admin Panel: http://localhost:8000/static/admin.html"
    echo "📚 API Documentation: http://localhost:8000/docs"
    echo
    echo "📋 To view logs:"
    if [ "$1" = "compose" ]; then
        echo "   $DOCKER_COMPOSE_CMD logs -f"
    else
        echo "   docker logs -f $CONTAINER_NAME"
    fi
    echo
    echo "🛑 To stop the application:"
    if [ "$1" = "compose" ]; then
        echo "   $DOCKER_COMPOSE_CMD down"
    else
        echo "   docker stop $CONTAINER_NAME"
    fi
    echo
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -c, --compose     Use Docker Compose for deployment (default)"
    echo "  -d, --docker      Use plain Docker for deployment"
    echo "  -b, --build-only  Build the Docker image only"
    echo "  -s, --status      Show current deployment status"
    echo "  -h, --help        Show this help message"
    echo
    echo "Examples:"
    echo "  $0                Deploy using Docker Compose"
    echo "  $0 --docker       Deploy using plain Docker"
    echo "  $0 --build-only   Build Docker image without deploying"
    echo "  $0 --status       Show current deployment status"
}

# Main deployment function
main() {
    local deployment_type="compose"
    local build_only=false
    local show_status_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--compose)
                deployment_type="compose"
                shift
                ;;
            -d|--docker)
                deployment_type="docker"
                shift
                ;;
            -b|--build-only)
                build_only=true
                shift
                ;;
            -s|--status)
                show_status_only=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Show status only
    if [ "$show_status_only" = true ]; then
        show_status "$deployment_type"
        exit 0
    fi
    
    # Pre-deployment checks
    check_docker
    
    if [ "$deployment_type" = "compose" ]; then
        check_docker_compose
    fi
    
    setup_env_file
    
    # Build image
    build_image
    
    if [ "$build_only" = true ]; then
        print_success "Build completed. Image '$IMAGE_NAME' is ready."
        exit 0
    fi
    
    # Deploy application
    if [ "$deployment_type" = "compose" ]; then
        deploy_compose
    else
        cleanup_existing
        deploy_docker
    fi
    
    # Check health and show status
    if check_health; then
        show_status "$deployment_type"
    else
        print_error "Deployment may have failed. Please check the logs."
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
