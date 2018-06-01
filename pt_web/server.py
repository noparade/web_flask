from app import create_app

app = create_app()

# 5001 for test
# 5000 for real
app.run('0.0.0.0', port=5000)
