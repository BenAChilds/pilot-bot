# Use Alpine Linux as the base image
FROM python:3.12-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot script and other necessary files into the container
COPY bot.py .
COPY welcome_message.md .

# Expose the port (optional, not necessary for a basic bot)
EXPOSE 8000

# Define the default command to run the bot
CMD ["python", "bot.py"]
