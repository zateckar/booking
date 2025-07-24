# Booking Application

A modern FastAPI-based booking system with OIDC authentication, administrative dashboard, and advanced reporting capabilities.

## Features

- **OIDC Authentication**: Secure login with OpenID Connect providers
- **Parking Space Management**: Manage parking lots and spaces
- **Booking System**: User-friendly booking interface
- **Administrative Dashboard**: Comprehensive admin panel
- **Dynamic Reports**: Customizable reporting with scheduling
- **Email Notifications**: Automated email system
- **Timezone Support**: Multi-timezone aware application
- **Backup System**: Automated backup functionality
- **Claims Mapping**: Advanced OIDC claims handling
- **Logging**: Comprehensive audit logging

## Tech Stack

- **Backend**: FastAPI (Python 3.13+)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: OIDC with Authlib
- **Frontend**: HTML/CSS/JavaScript with Bootstrap
- **Scheduler**: Background task scheduling
- **Email**: SendGrid API integration
- **Reports**: Excel export with openpyxl

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose
- Git

### Running the Application

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd booking
   ```

2. **Create environment file** (copy from example and customize):
   ```bash
   cp .env.example .env
   # Edit .env with your admin credentials:
   # - INITIAL_ADMIN_EMAIL (your admin email)
   # - INITIAL_ADMIN_PASSWORD (your admin password)
   ```

3. **Start with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Main application: http://localhost:8000
   - Admin dashboard: http://localhost:8000/static/admin.html
   - Login with the credentials you set in `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD`

### Environment Variables

Create a `.env` file in the root directory with only the essential variables:

```env
# Initial Admin User (for first-time setup)
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=change-this-secure-password
```

**Note**: All other configuration (OIDC, Email, Database settings, etc.) is done through the admin panel interface after logging in.

#### Initial Admin User Setup

The application can automatically create an initial admin user on first startup using environment variables:

- **INITIAL_ADMIN_EMAIL**: Email address for the admin user
- **INITIAL_ADMIN_PASSWORD**: Password for the admin user

When the application starts for the first time, it will:
1. Check if a user with the specified email already exists
2. If not, create a new admin user with the provided credentials
3. Hash the password securely using bcrypt
4. Set the user as an administrator

**Important Notes:**
- These credentials are only used for initial setup
- Once created, the admin user persists in the database
- You can remove these environment variables after the initial setup
- The admin user can then configure additional users and OIDC providers through the admin panel

## Development Setup

### Prerequisites

- Python 3.13+
- UV package manager (recommended) or pip

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd booking
   ```

2. **Install dependencies** (using UV):
   ```bash
   uv sync
   ```

   Or with pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python run.py
   ```

4. **Access the application**:
   - Main application: http://localhost:8000
   - Admin dashboard: http://localhost:8000/static/admin.html

### Project Structure

```
booking/
├── src/booking/           # Main application package
│   ├── models/           # Database models
│   ├── routers/          # API route handlers
│   │   └── admin/        # Admin API endpoints
│   ├── database.py       # Database configuration
│   ├── scheduler.py      # Background task scheduler
│   ├── email_service.py  # Email functionality
│   └── oidc.py          # OIDC authentication
├── static/              # Static assets (CSS, JS, images)
│   ├── css/
│   └── js/
│       └── admin/       # Admin dashboard frontend
├── templates/           # Jinja2 templates
├── Dockerfile          # Docker container definition
├── docker-compose.yml  # Multi-container orchestration
├── pyproject.toml      # Python project configuration
└── run.py              # Application entry point
```

## Configuration

### OIDC Providers

Configure OIDC providers through the admin dashboard:

1. Access admin panel: `/static/admin.html`
2. Navigate to "OIDC Providers"
3. Add your OIDC provider details:
   - Issuer URL
   - Client ID and Secret
   - Scopes
   - Claims mapping

### Email Settings

Configure email settings through the admin dashboard:

1. Access admin panel: `/static/admin.html`
2. Navigate to "Email Settings"  
3. Configure SendGrid API key and sender details

### Backup Settings

Configure automated backups:

1. Access admin panel: `/static/admin.html`
2. Navigate to "Backup Settings"
3. Set backup frequency and retention

## Deployment

### GitHub Actions CI/CD

The repository includes GitHub Actions workflow for automated building and deployment:

- **Build**: Builds Docker image on every push
- **Test**: Runs automated tests (if configured)
- **Deploy**: Pushes image to GitHub Container Registry

### Manual Deployment

1. **Build the Docker image**:
   ```bash
   docker build -t booking-app .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     --name booking-app \
     -p 8000:8000 \
     -v booking_data:/app/data \
     -e INITIAL_ADMIN_EMAIL=your-admin@example.com \
     -e INITIAL_ADMIN_PASSWORD=your-secure-password \
     booking-app
   ```

### Production Considerations

1. **Security**:
   - Change the default `SECRET_KEY`
   - Use HTTPS in production
   - Configure proper CORS settings
   - Use secure cookie settings

2. **Database**:
   - Consider PostgreSQL for production
   - Set up regular database backups
   - Monitor database performance

3. **Monitoring**:
   - Set up application logging
   - Monitor resource usage
   - Configure health checks

4. **Scaling**:
   - Use a reverse proxy (nginx)
   - Consider horizontal scaling
   - Implement load balancing

## API Documentation

Once the application is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Common Issues

1. **Database locked errors**:
   - Ensure only one instance is accessing the SQLite database
   - Consider using PostgreSQL for production

2. **OIDC authentication failures**:
   - Verify OIDC provider configuration
   - Check network connectivity
   - Review application logs

3. **Email sending issues**:
   - Verify SendGrid API key configuration
   - Check SendGrid account status and limits
   - Review application logs for SendGrid API errors

### Logs

Application logs are available:
- Container logs: `docker logs booking-app`
- Admin panel: Access logs through the admin dashboard

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the application logs for error details
- Review the admin dashboard for system status
