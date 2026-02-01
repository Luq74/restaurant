from main import app

# Vercel entry point
# No additional handler needed if using vercel.json rewrites to main:app
# But if we use @vercel/python, we might need this.
# For Vercel, simply exposing 'app' variable is often enough if configured correctly.
