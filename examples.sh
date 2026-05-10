#!/bin/bash
# TechKraft API Example Requests
# Run this script to test various endpoints via cURL.

BASE="http://localhost:8000"

echo "--- 1. Registering a Reviewer ---"
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","password":"Pass1234!"}'
echo -e "\n\n"

echo "--- 2. Logging in as Admin to get Token ---"
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@techkraft.com","password":"Admin1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$TOKEN" ]; then
    echo "Login failed. Is the server running on $BASE?"
    exit 1
fi
echo "Acquired Token!"
echo -e "\n"

echo "--- 3. Listing Candidates (Fuzzy Search & Pagination) ---"
curl -n -s "$BASE/candidates?status=new&role_applied=engineer&limit=5&offset=0" \
  -H "Authorization: Bearer $TOKEN"
echo -e "\n\n"

# Fetch a dynamic candidate ID to test the rest of the endpoints
echo "--- Fetching a Candidate ID for detailed tests ---"
CANDIDATE_ID=$(curl -s "$BASE/candidates?limit=1" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('items', [{}])[0].get('id', ''))")

if [ -n "$CANDIDATE_ID" ]; then
    echo "Using Candidate ID: $CANDIDATE_ID"
    echo -e "\n"

    echo "--- 4. Getting Candidate Detail ---"
    curl -s $BASE/candidates/$CANDIDATE_ID -H "Authorization: Bearer $TOKEN"
    echo -e "\n\n"

    echo "--- 5. Submitting a Score ---"
    curl -s -X POST $BASE/candidates/$CANDIDATE_ID/scores \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"category":"Technical","score":4,"note":"Strong async patterns"}'
    echo -e "\n\n"

    echo "--- 6. Triggering AI Summary (Simulated 2s Delay) ---"
    curl -X POST $BASE/candidates/$CANDIDATE_ID/summary \
      -H "Authorization: Bearer $TOKEN"
    echo -e "\n\n"

    echo "--- 7. Admin: Update Internal Notes & Status ---"
    curl -s -X PATCH $BASE/candidates/$CANDIDATE_ID \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"internal_notes":"Strong culture fit","status":"reviewed"}'
    echo -e "\n\n"
    
    echo "✅ All tests completed."
else
    echo "No candidates found to run detailed tests on."
fi
