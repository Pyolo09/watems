from app import create_app

app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' makes the app accessible from other devices on the same WiFi
    app.run(debug=True, host='0.0.0.0', port=5000)
