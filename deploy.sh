#!/bin/bash

# Roofing Outreach AI - Deployment Script
# This script sets up and deploys the roofing outreach system

set -e

echo "🏠 Roofing Outreach AI - Deployment Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your API keys before continuing"
        read -p "Press Enter when you've configured your .env file..."
    fi
    
    print_status ".env file found"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p data logs credentials nginx/ssl
    
    # Set permissions
    chmod 755 data logs
    
    print_status "Directories created"
}

# Check API keys configuration
check_api_keys() {
    print_status "Checking API key configuration..."
    
    source .env
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-openai-api-key-here" ]; then
        print_error "OpenAI API key not configured in .env file"
        exit 1
    fi
    
    if [ -z "$TWILIO_ACCOUNT_SID" ] || [ "$TWILIO_ACCOUNT_SID" = "your-twilio-account-sid" ]; then
        print_error "Twilio credentials not configured in .env file"
        exit 1
    fi
    
    if [ -z "$SUPABASE_URL" ] || [ "$SUPABASE_URL" = "https://your-project.supabase.co" ]; then
        print_error "Supabase credentials not configured in .env file"
        exit 1
    fi
    
    print_status "API keys configured"
}

# Setup Google credentials
setup_google_credentials() {
    if [ ! -f "credentials/google-credentials.json" ]; then
        print_warning "Google credentials not found at credentials/google-credentials.json"
        print_warning "Google Calendar integration will be disabled"
        print_warning "To enable Google Calendar:"
        print_warning "1. Download your service account JSON file from Google Cloud Console"
        print_warning "2. Save it as credentials/google-credentials.json"
    else
        print_status "Google credentials found"
    fi
}

# Create nginx configuration
create_nginx_config() {
    print_status "Creating nginx configuration..."
    
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream streamlit {
        server roofing-agent:8501;
    }
    
    upstream api {
        server roofing-agent:8000;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        # Streamlit dashboard
        location / {
            proxy_pass http://streamlit;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # API endpoints
        location /api/ {
            proxy_pass http://api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
    
    print_status "Nginx configuration created"
}

# Build and start services
deploy_services() {
    print_status "Building Docker images..."
    docker-compose build
    
    print_status "Starting services..."
    docker-compose up -d
    
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_status "Services started successfully!"
    else
        print_error "Some services failed to start. Check logs with: docker-compose logs"
        exit 1
    fi
}

# Show status and URLs
show_status() {
    print_status "Deployment completed successfully!"
    echo ""
    echo "🎉 Your Roofing Outreach AI system is running!"
    echo ""
    echo "📊 Dashboard: http://localhost"
    echo "🔍 Streamlit Direct: http://localhost:8501"
    echo "📡 API Endpoint: http://localhost:8000"
    echo ""
    echo "📋 Useful commands:"
    echo "  View logs:        docker-compose logs -f"
    echo "  Stop services:    docker-compose down"
    echo "  Restart services: docker-compose restart"
    echo "  Update system:    ./deploy.sh --update"
    echo ""
    echo "⚠️  Important notes:"
    echo "  - Configure your .env file with real API keys"
    echo "  - Add Google credentials for calendar integration"
    echo "  - Monitor logs for any errors"
    echo "  - Set up SSL certificates for production use"
}

# Update deployment
update_deployment() {
    print_status "Updating deployment..."
    
    # Pull latest changes
    git pull origin main
    
    # Rebuild and restart
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    
    print_status "Update completed!"
}

# Backup data
backup_data() {
    print_status "Creating backup..."
    
    backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup data and logs
    cp -r data "$backup_dir/"
    cp -r logs "$backup_dir/"
    cp .env "$backup_dir/"
    
    # Backup database (if using local database)
    docker-compose exec -T redis redis-cli BGSAVE
    
    tar -czf "$backup_dir.tar.gz" "$backup_dir"
    rm -rf "$backup_dir"
    
    print_status "Backup created: $backup_dir.tar.gz"
}

# Main deployment function
main() {
    case "${1:-}" in
        --update)
            update_deployment
            ;;
        --backup)
            backup_data
            ;;
        --logs)
            docker-compose logs -f
            ;;
        --stop)
            print_status "Stopping services..."
            docker-compose down
            print_status "Services stopped"
            ;;
        --restart)
            print_status "Restarting services..."
            docker-compose restart
            print_status "Services restarted"
            ;;
        *)
            check_docker
            check_env_file
            create_directories
            check_api_keys
            setup_google_credentials
            create_nginx_config
            deploy_services
            show_status
            ;;
    esac
}

# Run main function with all arguments
main "$@"