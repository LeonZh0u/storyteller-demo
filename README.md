# storyteller-demo
## Quick Start

### 1. Start the Bot Server

1. Navigate to the server directory:
   ```bash
   cd server
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the `.env.example` file to `.env` and configure it:
    - Add your API keys.
5. Start the server:
   ```bash
   python src/server.py
   ```

### 2. Start the Web Client

1. Navigate to the `client/javascript` directory:

```bash
cd client/javascript
```

2. Install dependencies:

```bash
npm install
```

3. Run the client app:

```
npm run dev
```

4. Visit http://localhost:5173 in your browser.
