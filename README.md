# AI Invoice Management System

A Django-based invoice management system with AI-powered data extraction and analytics capabilities. This system handles invoice upload, processing, vendor management, and provides business analytics through both API endpoints and web interface.

## Features

### Core Functionality
- **Invoice Upload & Processing**: Support for PDF and image file uploads with AI-powered data extraction
- **Vendor Management**: Automatic vendor detection and management with address and business information
- **AI Data Extraction**: Uses OpenAI to extract structured data from invoice documents
- **Status Tracking**: Complete invoice workflow from upload to payment with status management
- **Duplicate Detection**: AI-powered duplicate invoice detection

### Analytics & Reporting
- **Expense Summaries**: Pre-calculated analytics by daily, weekly, monthly, quarterly, and yearly periods
- **Budget Alerts**: Configurable spending alerts and thresholds
- **Spending Trends**: Month-over-month spending analysis with percentage changes
- **Dashboard Metrics**: Cached metrics for quick dashboard loading

### AI Processing
- **Data Extraction**: Extract invoice numbers, dates, amounts, vendor information, and line items
- **Vendor Normalization**: Intelligent vendor name matching with existing database entries
- **Confidence Scoring**: AI confidence ratings for extracted data
- **Processing Logs**: Comprehensive logging of all AI processing attempts and results

## Technology Stack

- **Backend**: Django 5.2.6 with Python 3.13
- **Database**: SQLite (development) with PostgreSQL-ready configuration
- **API**: Django REST Framework with session-based authentication
- **AI**: OpenAI GPT-4o-mini for document processing
- **File Handling**: Support for PDF and image uploads (10MB limit)
- **Frontend**: HTML templates with AJAX integration

## Installation & Setup

### Prerequisites
- Python 3.13+
- Django 5.2.6
- OpenAI API key

### Quick Start

1. **Install Dependencies**
   ```bash
   pip install django djangorestframework django-cors-headers django-filter python-decouple openai
   ```

2. **Environment Configuration**
   Create a `.env` file in the project root:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_MAX_TOKENS=2000
   OPENAI_TEMPERATURE=0.1
   ```

3. **Database Setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

## Project Structure

### Django Applications

**users** - User management and authentication
- Custom User model with email-based authentication
- UserProfile for extended user information and preferences
- Company and business information support

**invoices** - Core invoice processing
- Invoice model with comprehensive metadata and AI processing fields
- Vendor management with address and business details
- InvoiceItem for line-item details
- InvoiceProcessingLog for tracking AI operations
- File upload handling for PDFs and images

**analytics** - Business intelligence and reporting
- ExpenseSummary for pre-calculated analytics by time periods
- BudgetAlert for spending notifications and thresholds
- SpendingTrend for month-over-month analysis
- UserDashboardMetrics for cached dashboard data

**ai_processing** - AI task management
- AIProcessingTask for tracking various AI operations
- OpenAI service integration for data extraction
- Support for data extraction, vendor recognition, and duplicate detection

## API Endpoints

All API endpoints are prefixed with `/api/`:

- `/api/auth/` - User authentication and profile management
- `/api/invoices/` - Invoice CRUD operations and file uploads
- `/api/analytics/` - Analytics and reporting endpoints
- `/api/ai/` - AI processing task management

### Authentication
The system uses session-based authentication with CSRF protection. DRF browsable API is available at `/api-auth/` for development.

## Database Schema

### Key Models

**Invoice Status Flow**: pending → processing → processed → approved → paid

**User Isolation**: All user data is properly filtered and isolated per user account

**AI Processing**: JSON fields store extracted data with confidence scores

**Indexing**: Optimized database indexes on frequently queried fields

## Configuration

### File Uploads
- Maximum file size: 10MB
- Supported formats: PDF, JPG, PNG
- Files organized by date in subdirectories under `/media/invoices/`

### CORS Configuration
Configured for frontend integration:
- React (localhost:3000)
- Vue.js (localhost:8080)

### OpenAI Configuration
- Model: GPT-4o-mini (configurable)
- Max tokens: 2000 (configurable)
- Temperature: 0.1 for consistent results

## Development Commands

```bash
# Database operations
python manage.py makemigrations
python manage.py migrate
python manage.py flush  # Reset database

# Server management
python manage.py runserver
python manage.py collectstatic

# User management
python manage.py createsuperuser

# Development tools
python manage.py shell
python manage.py check
python manage.py test
```

## Frontend Integration

The system includes both API endpoints and web interface:

### Web Interface Routes
- `/` - Dashboard home page
- `/login/` - User authentication
- `/upload/` - Invoice upload interface
- `/invoices/` - Invoice list and management
- `/analytics/` - Analytics dashboard

### AJAX Support
- Asynchronous file upload with progress tracking
- Real-time status updates for AI processing

## AI Processing Features

### Data Extraction
Extracts the following information from invoices:
- Invoice number and dates (issue date, due date)
- Vendor information (name, address, contact details)
- Financial data (subtotal, tax, total amount)
- Line items with descriptions, quantities, and prices
- Currency and payment terms

### Vendor Intelligence
- Automatic vendor normalization with fuzzy matching
- Vendor deduplication using existing database entries
- Automatic creation of new vendor records with extracted details

### Processing Workflow
1. File upload and validation
2. Text extraction from PDF/image
3. AI-powered data extraction
4. Vendor matching and normalization
5. Duplicate detection
6. Data validation and storage
7. Analytics update

## Security

- CSRF protection enabled
- Session-based authentication
- File type validation for uploads
- User data isolation
- Secure file handling

## Development Notes

- Uses Django 5.2.6 with Python 3.13
- All models include proper `__str__` methods and metadata
- ViewSets follow DRF best practices with proper permissions
- User data is properly isolated using get_queryset() overrides
- AI processing tasks are tracked with comprehensive logging
- File uploads are organized by date in subdirectories

## License

This project is for educational and development purposes.