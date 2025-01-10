# Heroku Agent Flask Application

A Flask application that interfaces with Heroku's Managed Inference and Agent add-on to provide various tools including web browsing, database operations, code execution, PDF reading, and web search capabilities.

## Prerequisites

- Python 3.8+
- Heroku CLI installed and configured
- Heroku account with access to Managed Inference add-on
- PostgreSQL (for database operations)

## Local Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd <your-repo-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```bash
HEROKU_API_KEY=your_heroku_api_key
HEROKU_APP_NAME=your_app_name
HEROKU_MANAGED_INFERENCE_API_KEY=your_managed_inference_key
APP_API_KEY=your_app_api_key
DATABASE_URL=your_postgres_database_url
```

## Heroku Deployment

1. Initialize a git repository (if not already done):
```bash
git init
git add .
git commit -m "Initial commit"
```

2. Create a new Heroku app:
```bash
heroku create your-app-name
```

3. Add PostgreSQL to your Heroku app:
```bash
heroku addons:create heroku-postgresql:standard-0
```

4. Add the Managed Inference add-on:
```bash
heroku addons:create managed-inference:standard
```

5. Configure environment variables:
```bash
heroku config:set HEROKU_API_KEY=$(heroku auth:token)
heroku config:set HEROKU_APP_NAME=your-app-name
heroku config:set APP_API_KEY=your_chosen_api_key
```

Note: The `HEROKU_MANAGED_INFERENCE_API_KEY` will be automatically set when you add the managed-inference add-on.

6. Deploy the application:
```bash
git push heroku main
```

7. Ensure at least one dyno is running:
```bash
heroku ps:scale web=1
```

## API Endpoints

All endpoints require the `X-API-Key` header matching your `APP_API_KEY`.

### Web Browsing

#### Single Page
```bash
POST /browse
Content-Type: application/json
X-API-Key: your_api_key

{
    "url": "https://example.com"
}
```

#### Multi-Page
```bash
POST /browse-multi
Content-Type: application/json
X-API-Key: your_api_key

{
    "urls": [
        "https://example.com",
        "https://example.org"
    ]
}
```

### Database Operations

#### Get Schema
```bash
GET /database/schema?database_url=your_database_url
X-API-Key: your_api_key
```

#### Run Query
```bash
POST /database/query
Content-Type: application/json
X-API-Key: your_api_key

{
    "query": "SELECT * FROM users LIMIT 10;",
    "database_url": "your_database_url"
}
```

### Code Execution
```bash
POST /code/execute
Content-Type: application/json
X-API-Key: your_api_key

{
    "code": "print('Hello, World!')",
    "language": "python"
}
```

### Dyno Commands
```bash
POST /dyno/command
Content-Type: application/json
X-API-Key: your_api_key

{
    "command": "ls -la"
}
```

### PDF Reading
```bash
POST /pdf/read
Content-Type: application/json
X-API-Key: your_api_key

{
    "pdf_url": "https://example.com/document.pdf"
}
```

### Web Search
```bash
POST /search
Content-Type: application/json
X-API-Key: your_api_key

{
    "query": "your search query"
}
```

## Error Handling

All endpoints return JSON responses with the following structure:

- Success: `{"result": data}`
- Error: `{"error": "error message"}`

HTTP status codes:
- 200: Success
- 400: Bad Request (missing or invalid parameters)
- 401: Unauthorized (invalid or missing API key)
- 500: Internal Server Error

## Database Security

When working with PostgreSQL:

1. Always use parameterized queries to prevent SQL injection
2. Keep your database URL secure and never commit it to version control
3. Use connection pooling for better performance
4. Set appropriate connection limits in your database configuration

## Monitoring and Logging

1. View application logs:
```bash
heroku logs --tail
```

2. Monitor dyno status:
```bash
heroku ps
```

3. Check add-on status:
```bash
heroku addons
```

## Best Practices

1. Regularly update dependencies to patch security vulnerabilities
2. Monitor your API usage to stay within Heroku's limits
3. Implement rate limiting for your endpoints
4. Keep your API keys secure and rotate them regularly
5. Back up your database regularly

## Environment Variables Reference

- `HEROKU_API_KEY`: Your Heroku API key
- `HEROKU_APP_NAME`: Your Heroku application name
- `HEROKU_MANAGED_INFERENCE_API_KEY`: API key for the Managed Inference add-on
- `APP_API_KEY`: Your application's API key for endpoint authentication
- `DATABASE_URL`: PostgreSQL database URL (automatically set by Heroku PostgreSQL add-on)

## Troubleshooting

1. If the application fails to start, check the logs:
```bash
heroku logs --tail
```

2. If database connections fail:
   - Verify the DATABASE_URL is correctly set
   - Check if the database is properly provisioned
   - Ensure you're within your connection limits

3. If add-on features aren't working:
   - Verify the add-on is properly installed
   - Check if you have the correct plan level
   - Ensure API keys are correctly set

## Support

For issues related to:
- Heroku platform: Contact Heroku support
- Managed Inference add-on: Contact Heroku Managed Inference support
- Application code: Open an issue in the repository

