# --- Stage 1: Build the React Frontend ---
FROM node:18-alpine AS frontend-builder

# Set the working directory for the frontend
WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy the rest of the frontend code and build it
COPY frontend/ ./
RUN npm run build


# --- Stage 2: Build the Python Backend ---
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory for the backend
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . .

# Copy the built React app from the first stage
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Run collectstatic to gather all static files (Django + React)
RUN python manage.py collectstatic --no-input

# Expose the port that Gunicorn will run on
EXPOSE 8080

# The command to run the application
# App Platform provides the $PORT variable automatically
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "clinic_help_desk.wsgi"]