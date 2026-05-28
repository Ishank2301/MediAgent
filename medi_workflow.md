# N8N System Design Guide: Medication Management Workflow
## Hackathon Edition (24-Hour Build)

**Target Stack**: n8n + Tesseract OCR + Llama3 (Local) + Streamlit + Cloud Storage

---

## 📋 Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Core Components Breakdown](#core-components-breakdown)
3. [N8N Workflow Structure](#n8n-workflow-structure)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Implementation Phases](#implementation-phases)
6. [Integration Points](#integration-points)
7. [Optimization Tips for Hackathon](#optimization-tips-for-hackathon)

---

## System Architecture Overview

Your medication management system will operate as a **distributed workflow** with three main layers:

**Frontend Layer** (Streamlit) → **Orchestration Layer** (n8n) → **Processing Layer** (Tesseract + Llama3 + Storage)

The n8n instance acts as the central nervous system, coordinating all operations. Since you're running locally on your laptop, n8n will run as a self-hosted instance, receiving requests from Streamlit and returning processed results.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      STREAMLIT FRONTEND                         │
│  (User Input → Upload/Manual Entry → Display Results)           │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST API Calls
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    N8N ORCHESTRATION LAYER                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Webhook Trigger → Route → Process → Respond             │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  TESSERACT   │  │  LLAMA3 LLM  │  │   STORAGE    │
│   (OCR)      │  │  (Analysis)  │  │  (Database)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Core Components Breakdown

### 1. **Input Processing Layer**

This layer handles two input methods:

**Method A: Image Upload (OCR Path)**
- User uploads prescription image via Streamlit
- Streamlit sends image to n8n webhook
- n8n calls Tesseract OCR (local binary)
- Extracted text is cleaned and validated

**Method B: Manual Entry (Direct Path)**
- User enters medication details in Streamlit form
- Data is validated client-side
- Sent directly to n8n for processing

**Key Decision**: Both paths must converge at a "Data Normalization" node in n8n where you standardize the format (medication name, dosage, frequency, etc.).

### 2. **Data Validation & Cleaning**

Before any analysis, n8n must normalize the data:

- **Medication Name Standardization**: Convert "Aspirin 500mg" → standardized format
- **Dosage Parsing**: Extract quantity and unit (e.g., "500mg")
- **Frequency Parsing**: Convert "twice daily" → "2x per day"
- **Duration Extraction**: Identify treatment period if provided

This is critical because Tesseract OCR might extract messy text like "Asp1r1n" or "500 m g" that needs cleanup.

### 3. **Database Lookup Layer**

You need a local or cloud-based drug database. For a hackathon, consider:

**Option A: Local SQLite Database** (Fastest for hackathon)
- Download a free drug database (e.g., DrugBank lite)
- Store locally on your laptop
- n8n queries it directly

**Option B: Cloud API** (More scalable)
- Use free APIs like RxNorm or DrugBank API
- n8n makes HTTP calls to fetch drug data
- Slower but no local setup needed

**Recommendation**: Use SQLite locally. You can download a CSV of common drugs and medications and import into SQLite in 5 minutes.

**Data to Store**: Drug name, active ingredients, side effects, contraindications, food interactions, allergy information.

### 4. **Parallel Analysis Layer**

This is where n8n's strength shines. You'll create three parallel workflows:

**Workflow A: Drug-Drug Interactions**
- Input: List of medications
- Process: Compare against interaction database
- Output: Interaction pairs with severity levels

**Workflow B: Allergy Checking**
- Input: User's allergy profile + medications
- Process: Cross-reference with drug ingredients
- Output: Allergy warnings

**Workflow C: Food-Drug Interactions**
- Input: Medications + common foods
- Process: Check interaction database
- Output: Food restrictions

**Why Parallel?** These three analyses are independent. Running them simultaneously (not sequentially) saves time. n8n's "Merge" node combines results afterward.

### 5. **GenAI Analysis Layer (Llama3)**

This layer generates human-readable explanations:

**Input to Llama3**:
```
User Profile:
- Age: 45
- Allergies: Penicillin
- Current Medications: [list]
- Dietary Restrictions: Vegetarian

Analysis Results:
- Drug-Drug Interactions: [list]
- Allergy Warnings: [list]
- Food Interactions: [list]

Task: Generate a personalized medication safety report explaining:
1. Why these interactions matter for this user
2. What precautions to take
3. When to contact a doctor
```

**Llama3 Processing**:
- Run locally on your laptop (requires 8GB+ RAM)
- n8n sends prompt via local API (e.g., Ollama or LM Studio)
- Returns generated text
- n8n formats and stores response

**Customization**: The prompt can be tailored per user by including their medical history, age, allergies, etc.

### 6. **Risk Assessment Layer**

Calculate an overall risk score:

```
Risk Score = (Drug-Drug Interaction Severity × 0.4) 
           + (Allergy Match Count × 0.35) 
           + (Food Interaction Severity × 0.25)

Score Range: 0-100
- 0-20: Low Risk (Green)
- 21-50: Moderate Risk (Yellow)
- 51-100: High Risk (Red)
```

This is a simple calculation node in n8n. You can customize weights based on your definition of "critical."

### 7. **Output Generation Layer**

Generate three output types:

**Output A: Medication Report**
- Summary of all medications
- Identified interactions
- Risk score
- AI-generated recommendations

**Output B: Alert System**
- Critical alerts (High Risk)
- Warnings (Moderate Risk)
- Informational notes (Low Risk)
- Can be logged to Streamlit or sent via email/SMS

**Output C: Dashboard Update**
- Store results in cloud storage (Firebase, AWS S3, or Supabase)
- Streamlit queries this storage to display results
- Enables real-time updates

### 8. **Persistence Layer**

Store everything for tracking adherence:

- **User Profile**: Medical history, allergies, preferences
- **Medication History**: All prescriptions and analyses
- **Interaction Database**: Cached results for faster lookups
- **Audit Log**: Timestamps, user actions, system decisions

Use cloud storage (Firebase Firestore, Supabase, or MongoDB Atlas free tier) for easy access from both n8n and Streamlit.

---

## N8N Workflow Structure

You'll build **3 main workflows** in n8n:

### Workflow 1: "Medication Input Handler"
**Purpose**: Accept input from Streamlit, route to appropriate processor

**Nodes**:
1. **Webhook Trigger** - Listens for POST requests from Streamlit
2. **Router Node** - Checks if input is image or text
3. **IF: Image Path**
   - Tesseract OCR Node (calls local Tesseract binary)
   - Text Cleaning Node (regex, standardization)
4. **IF: Text Path**
   - Validation Node (check format)
5. **Data Normalization Node** - Standardize both paths
6. **Save to Database** - Store raw input
7. **Trigger Workflow 2** - Call analysis workflow

**Flow**: `Webhook → Router → Process → Normalize → Save → Trigger Next`

### Workflow 2: "Medication Analysis Engine"
**Purpose**: Run all analysis in parallel

**Nodes**:
1. **Start Node** - Receives data from Workflow 1
2. **Database Lookup** - Fetch drug data
3. **Parallel Execution**:
   - **Branch A**: Drug-Drug Interaction Check
   - **Branch B**: Allergy Check
   - **Branch C**: Food-Drug Interaction Check
4. **Merge Node** - Combine results from all branches
5. **Risk Calculation** - Compute overall risk score
6. **Trigger Workflow 3** - Pass results to GenAI

**Flow**: `Start → Lookup → [Parallel A, B, C] → Merge → Calculate → Trigger Next`

### Workflow 3: "AI Report Generation & Storage"
**Purpose**: Generate human-readable report and store results

**Nodes**:
1. **Start Node** - Receives analysis results
2. **Llama3 Prompt Builder** - Construct prompt with user context
3. **Llama3 API Call** - Send to local LLM
4. **Response Formatter** - Clean up AI output
5. **Alert Generator** - Create alerts based on risk level
6. **Cloud Storage Save** - Store complete report
7. **Webhook Response** - Return results to Streamlit

**Flow**: `Start → Build Prompt → Call LLM → Format → Generate Alerts → Save → Return`

### Optional Workflow 4: "Adherence Tracker" (If time permits)
**Purpose**: Monitor medication adherence over time

**Nodes**:
1. **Scheduled Trigger** - Runs daily at set time
2. **Query User Data** - Fetch medication schedule
3. **Check Adherence** - Compare scheduled vs. taken
4. **Generate Report** - Create adherence summary
5. **Send Notification** - Alert user if missed doses

---

## Data Flow Architecture

### Complete End-to-End Flow

```
USER INTERACTION (Streamlit)
    ↓
1. Upload prescription image OR enter medication manually
    ↓
2. Streamlit sends HTTP POST to n8n webhook
    ↓
N8N PROCESSING
    ↓
3. Workflow 1: Route input (image vs. text)
    ├─ If image: OCR with Tesseract
    └─ If text: Validate format
    ↓
4. Normalize data to standard format
    ↓
5. Query SQLite/Cloud drug database
    ↓
6. Workflow 2: Run 3 parallel analyses
    ├─ Drug-Drug Interactions
    ├─ Allergy Checking
    └─ Food-Drug Interactions
    ↓
7. Merge results and calculate risk score
    ↓
8. Workflow 3: Generate AI analysis via Llama3
    ↓
9. Create alerts based on risk level
    ↓
10. Save complete report to cloud storage
    ↓
11. Return results to Streamlit via webhook response
    ↓
STREAMLIT DISPLAY
    ↓
12. Display report, risk score, alerts, recommendations
    ↓
13. User can save/share/track adherence
```

### Data Structures

**Input Data Structure** (from Streamlit):
```json
{
  "user_id": "user_123",
  "input_type": "image" | "text",
  "image_path": "path/to/prescription.jpg" | null,
  "medications": [
    {
      "name": "Aspirin",
      "dosage": "500mg",
      "frequency": "2x daily",
      "duration": "7 days"
    }
  ],
  "user_profile": {
    "age": 45,
    "allergies": ["Penicillin"],
    "medical_history": ["Hypertension"],
    "dietary_restrictions": []
  }
}
```

**Output Data Structure** (to Streamlit):
```json
{
  "status": "success",
  "risk_score": 35,
  "risk_level": "moderate",
  "medications": [...],
  "interactions": {
    "drug_drug": [...],
    "allergies": [...],
    "food_interactions": [...]
  },
  "ai_analysis": "Generated report text...",
  "alerts": [
    {
      "type": "warning",
      "message": "Aspirin may cause bleeding if combined with..."
    }
  ],
  "recommendations": [...]
}
```

---

## Implementation Phases

### Phase 1: Foundation (Hours 0-4)
**Goal**: Get basic infrastructure running

**Tasks**:
1. Install n8n locally on laptop
2. Install Tesseract OCR binary
3. Set up Llama3 locally (via Ollama or LM Studio)
4. Create SQLite database with drug data
5. Set up cloud storage (Firebase/Supabase)
6. Create basic Streamlit app skeleton

**Deliverable**: All tools running, n8n accessible at localhost:5678

### Phase 2: Input Processing (Hours 4-8)
**Goal**: Build Workflow 1

**Tasks**:
1. Create webhook in n8n
2. Build Tesseract OCR integration
3. Create text validation logic
4. Build data normalization node
5. Test with sample prescriptions
6. Connect to Streamlit

**Deliverable**: Upload image → Extract text → Normalize data

### Phase 3: Analysis Engine (Hours 8-14)
**Goal**: Build Workflow 2

**Tasks**:
1. Set up SQLite connection in n8n
2. Build drug-drug interaction checker
3. Build allergy checker
4. Build food-drug interaction checker
5. Create parallel execution
6. Implement risk scoring
7. Test with multiple medications

**Deliverable**: Input medications → Get interaction analysis → Risk score

### Phase 4: AI & Output (Hours 14-20)
**Goal**: Build Workflow 3

**Tasks**:
1. Connect Llama3 API to n8n
2. Build prompt templating
3. Create response formatter
4. Build alert generator
5. Set up cloud storage integration
6. Create webhook response handler
7. Test end-to-end flow

**Deliverable**: Full analysis → AI report → Alerts → Storage

### Phase 5: Frontend Integration & Polish (Hours 20-24)
**Goal**: Complete Streamlit app and testing

**Tasks**:
1. Build Streamlit UI for all features
2. Connect to n8n workflows
3. Display results beautifully
4. Add error handling
5. Test edge cases
6. Performance optimization
7. Final testing and demo preparation

**Deliverable**: Complete working application ready for demo

---

## Integration Points

### N8N ↔ Streamlit Integration

**Streamlit sends to n8n**:
```python
import requests
import json

response = requests.post(
    'http://localhost:5678/webhook/medication-input',
    json={
        'user_id': 'user_123',
        'input_type': 'text',
        'medications': [...],
        'user_profile': {...}
    }
)
result = response.json()
```

**N8N returns to Streamlit**:
- Webhook response with complete analysis
- Results stored in cloud storage for persistence
- Streamlit can query storage for historical data

### N8N ↔ Tesseract Integration

**In n8n**:
- Use "Execute Command" node to call Tesseract binary
- Command: `tesseract /path/to/image.jpg stdout`
- Parse output text
- Clean and normalize

### N8N ↔ Llama3 Integration

**Two approaches**:

**Approach A: Ollama (Recommended for hackathon)**
- Install Ollama: `ollama pull llama2` (or llama3 if available)
- Ollama runs local API on `http://localhost:11434`
- n8n makes HTTP POST to `/api/generate`
- Simple and fast

**Approach B: LM Studio**
- GUI-based local LLM runner
- Also exposes local API
- More user-friendly but slightly slower

**N8N Configuration**:
- HTTP Request node
- URL: `http://localhost:11434/api/generate`
- Method: POST
- Body: `{"model": "llama2", "prompt": "...", "stream": false}`

### N8N ↔ SQLite Integration

**In n8n**:
- Use SQLite node (available in n8n)
- Database file: `/path/to/drugs.db`
- Query: `SELECT * FROM drugs WHERE name LIKE ?`
- Cache results for performance

### N8N ↔ Cloud Storage Integration

**Firebase Firestore** (Recommended):
- Free tier: 1GB storage, 50k reads/day
- n8n has Firebase integration
- Store user profiles, medication history, reports
- Real-time sync to Streamlit

**Alternative: Supabase**
- PostgreSQL backend
- Free tier: 500MB storage
- Better for complex queries
- n8n has PostgreSQL integration

---

## Optimization Tips for Hackathon

### 1. **Time-Saving Strategies**

**Use Templates**: n8n has pre-built templates. Start with webhook template and build from there.

**Pre-load Data**: Download drug database beforehand. Don't spend time building it during hackathon.

**Cache Results**: Store common drug interactions in memory to avoid repeated lookups.

**Parallel Execution**: Run all three analyses simultaneously (n8n's strength). Don't do them sequentially.

### 2. **Performance Optimization**

**Tesseract**: For faster OCR, preprocess images (grayscale, resize) before sending to Tesseract.

**Llama3**: Use a smaller model (7B parameters) instead of 13B or 70B for faster inference on laptop.

**Database**: Index drug names in SQLite for faster lookups.

**Caching**: Store recent queries in n8n's memory to avoid repeated API calls.

### 3. **Fallback Strategies**

**If Tesseract fails**: Fall back to manual entry prompt in Streamlit.

**If Llama3 is slow**: Use template-based report generation instead of full AI analysis.

**If cloud storage is slow**: Use local JSON files as backup.

**If n8n crashes**: Have workflow exports saved so you can quickly reimport.

### 4. **Testing Strategy**

**Unit Test Each Workflow**: Test Workflow 1, 2, 3 independently before connecting.

**Use Mock Data**: Create sample medication lists for testing without OCR.

**Test Edge Cases**: Empty input, unknown drugs, multiple allergies, etc.

**Performance Test**: Measure end-to-end latency with different input sizes.

### 5. **Debugging Tips**

**Enable Logging**: Turn on debug mode in n8n to see node execution details.

**Use Test Webhooks**: n8n has built-in webhook testing tool.

**Monitor Llama3**: Keep terminal open where Ollama runs to see inference logs.

**Check Database**: Use SQLite CLI to verify drug data is loaded correctly.

---

## Quick Reference: N8N Node Checklist

| Workflow | Node Type | Purpose | Config |
|----------|-----------|---------|--------|
| Workflow 1 | Webhook | Listen for Streamlit requests | POST, path: `/medication-input` |
| Workflow 1 | Router | Route image vs. text | Condition: `input_type === 'image'` |
| Workflow 1 | Execute Command | Call Tesseract | Command: `tesseract $image stdout` |
| Workflow 1 | Function | Text cleaning | Regex, standardization logic |
| Workflow 1 | SQLite | Save raw input | Insert into `inputs` table |
| Workflow 2 | SQLite | Drug lookup | Query `drugs` table |
| Workflow 2 | Function | Drug-Drug check | Compare against interaction DB |
| Workflow 2 | Function | Allergy check | Match against user allergies |
| Workflow 2 | Function | Food-Drug check | Query food interactions DB |
| Workflow 2 | Merge | Combine results | Combine all 3 branches |
| Workflow 2 | Function | Risk calculation | Calculate score formula |
| Workflow 3 | Function | Prompt builder | Template with user context |
| Workflow 3 | HTTP Request | Call Llama3 | POST to `localhost:11434/api/generate` |
| Workflow 3 | Function | Response format | Clean AI output |
| Workflow 3 | Function | Alert generator | Create alerts by risk level |
| Workflow 3 | Firebase | Save report | Store in Firestore |
| Workflow 3 | Webhook Response | Return to Streamlit | Send JSON response |

---

## Streamlit Integration Checklist

**Streamlit Features to Build**:
- [ ] Image upload widget
- [ ] Manual medication entry form
- [ ] User profile setup (age, allergies, medical history)
- [ ] Submit button that calls n8n webhook
- [ ] Loading spinner while n8n processes
- [ ] Results display (risk score, interactions, alerts)
- [ ] AI-generated report display
- [ ] Medication history view
- [ ] Adherence tracker
- [ ] Export report as PDF

---

## Local Setup Commands (Quick Reference)

```bash
# Install n8n
npm install -g n8n

# Start n8n
n8n start

# Install Tesseract (macOS)
brew install tesseract

# Install Tesseract (Ubuntu/Debian)
sudo apt-get install tesseract-ocr

# Install Ollama (for Llama3)
# Download from https://ollama.ai

# Start Ollama with Llama3
ollama pull llama2
ollama serve

# Create SQLite database
sqlite3 drugs.db < schema.sql

# Install Streamlit
pip install streamlit

# Run Streamlit app
streamlit run app.py
```

---

## Success Criteria for Hackathon

✅ **Minimum Viable Product (MVP)**:
- Image upload → OCR → Text extraction
- Manual medication entry
- Drug database lookup
- Basic interaction checking
- Risk score calculation
- Streamlit UI

✅ **Nice to Have**:
- Llama3 AI analysis
- Parallel processing
- Cloud storage integration
- Adherence tracking
- Beautiful UI

✅ **Demo-Ready**:
- No crashes during demo
- Handles 5+ medications
- Generates report in <10 seconds
- Clear, understandable output

---

## Potential Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Tesseract OCR accuracy | Preprocess images, use high-quality scans, have manual fallback |
| Llama3 slow inference | Use smaller model (7B), run on GPU if available, cache responses |
| N8N crashes under load | Increase memory allocation, optimize database queries, use caching |
| Drug database incomplete | Use free APIs as fallback (RxNorm, DrugBank), crowdsource common drugs |
| Streamlit-n8n latency | Use async webhooks, implement loading states, optimize n8n workflows |
| Cloud storage integration | Have local JSON backup, test connectivity early, use free tier limits |

---

## Final Recommendations

1. **Start Simple**: Get basic flow working first (input → process → output), then add complexity.

2. **Use Existing Tools**: Don't build from scratch. Use n8n templates, free drug APIs, pre-built OCR.

3. **Test Early**: Test each workflow independently before connecting them.

4. **Optimize Late**: Get it working first, optimize performance in final hours.

5. **Document as You Go**: Keep notes on what works/doesn't for final presentation.

6. **Have Backups**: Export n8n workflows, save database dumps, keep code in Git.

7. **Focus on Demo**: Make the happy path (normal use case) work perfectly. Edge cases can be handled later.

---

## Resources for Hackathon

**N8N**:
- Official Docs: https://docs.n8n.io
- Community Forum: https://community.n8n.io
- YouTube Tutorials: Search "n8n workflow tutorial"

**Tesseract OCR**:
- GitHub: https://github.com/UB-Mannheim/tesseract/wiki
- Python Wrapper: `pip install pytesseract`

**Llama3 / Ollama**:
- Ollama: https://ollama.ai
- Model Library: https://ollama.ai/library

**Drug Databases**:
- RxNorm API: https://rxnav.nlm.nih.gov
- DrugBank: https://www.drugbank.ca
- OpenFDA: https://open.fda.gov

**Streamlit**:
- Official Docs: https://docs.streamlit.io
- Component Gallery: https://streamlit.io/components

---

## Next Steps

1. **Read this guide** and understand the architecture
2. **Set up local environment** (n8n, Tesseract, Ollama, SQLite)
3. **Create n8n workflows** following the structure outlined
4. **Build Streamlit frontend** with UI components
5. **Integrate** Streamlit ↔ n8n
6. **Test** end-to-end flow
7. **Optimize** for performance
8. **Polish** for demo

**Good luck with your hackathon! 🚀**

---

## Document Info

- **Created for**: 24-Hour Hackathon Project
- **Target Audience**: 3rd Year CSE Student
- **Tech Stack**: n8n + Tesseract + Llama3 + Streamlit + Cloud Storage
- **Complexity**: Intermediate (assumes basic programming knowledge)
- **Estimated Implementation Time**: 20-24 hours
