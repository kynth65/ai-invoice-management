# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based invoice management system with AI processing capabilities. The system handles invoice upload, AI-powered data extraction, categorization, analytics, and user management.

## Common Development Commands

### Server Management
```bash
# Start development server
python manage.py runserver

# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run tests
python manage.py test

# Access Django shell
python manage.py shell

# Check project for issues
python manage.py check
```

### Database Operations
```bash
# Reset database (flush all data)
python manage.py flush

# Load fixture data
python manage.py loaddata <fixture_name>

# Dump data to fixture
python manage.py dumpdata <app_name> --indent=2 > <fixture_name>.json
```

## Architecture Overview

### Core Applications

1. **users** - Custom user model with authentication and profile management
   - Custom User model extending AbstractUser with email as USERNAME_FIELD
   - UserProfile for extended user information and preferences
   - Email-based authentication system

2. **invoices** - Main invoice processing and management
   - Invoice model with comprehensive metadata and AI processing fields
   - Category and Vendor models for organization
   - InvoiceItem for line-item details
   - InvoiceProcessingLog for tracking AI operations
   - File upload handling for PDFs and images

3. **analytics** - Business intelligence and reporting
   - ExpenseSummary for pre-calculated analytics by time periods
   - BudgetAlert for spending notifications
   - SpendingTrend for trend analysis
   - UserDashboardMetrics for cached dashboard data

4. **ai_processing** - AI task management and processing
   - AIProcessingTask for tracking various AI operations
   - Supports data extraction, categorization, duplicate detection

### Key Technical Details

- **Database**: SQLite for development (settings configured for easy PostgreSQL migration)
- **API Framework**: Django REST Framework with viewsets and serializers
- **Authentication**: Session-based with DRF integration
- **CORS**: Configured for frontend integration (React/Vue.js)
- **File Handling**: Media files stored in `/media/` with 10MB upload limits
- **Custom User Model**: `users.User` set as AUTH_USER_MODEL

### Database Schema Highlights

- **Invoice Status Flow**: pending → processing → processed → approved → paid
- **AI Processing**: JSON fields store extracted data and confidence scores
- **User Isolation**: All user data properly filtered by request.user
- **Indexing**: Optimized indexes on frequently queried fields

### API Structure

All APIs are prefixed with `/api/`:
- `/api/auth/` - User authentication and profile management
- `/api/invoices/` - Invoice CRUD operations and statistics
- `/api/analytics/` - Analytics and reporting endpoints
- `/api/ai/` - AI processing task management

### Frontend Integration

- CORS enabled for localhost:3000 (React) and localhost:8080 (Vue.js)
- DRF browsable API available at `/api-auth/` for development
- Session-based authentication with CSRF protection

### Important Configuration Notes

- Secret key is development-only (needs secure replacement for production)
- DEBUG=True for development
- Media and static files served by Django in development
- Custom file upload size limits set to 10MB
- Timezone set to UTC with i18n enabled

## Development Notes

- The project uses Django 5.2.6 with Python 3.13
- All models include proper `__str__` methods and metadata
- ViewSets follow DRF best practices with proper permissions
- User data is properly isolated using get_queryset() overrides
- File uploads are organized by date in subdirectories
- AI processing tasks are tracked with comprehensive logging