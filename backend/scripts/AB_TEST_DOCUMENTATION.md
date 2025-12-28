# A/B Testing: Single vs Hybrid Agent System

## Overview

This A/B test compares two approaches for handling B2B sales inquiries:

**Control (A)**: Current single `inbox-manager` agent
**Variant (B)**: Hybrid 2-agent system (triage + enhanced response)

## Hypothesis

The hybrid system will provide:
- Better intent detection
- More relevant KB document retrieval
- Higher quality responses
- Better formatting consistency

Trade-offs:
- Slightly higher latency (~100-500ms)
- Minimal additional cost

## Test Setup

### Test Queries (8 scenarios)

1. "What does your company do?" → MORE_INFO
2. "Do you have any case studies?" → CASE_STUDY_REQUEST
3. "How much does this cost?" → PRICING
4. "Can we schedule a call?" → BOOKING_REQUEST
5. "What industries have you worked with?" → MORE_INFO
6. "Follow up in 2 months" → LONG_FOLLOW_UP
7. "Tell me about your services" → MORE_INFO
8. "Show me examples of your work" → CASE_STUDY_REQUEST

### Metrics Collected

**Performance:**
- Response latency (total, triage, response)
- Token usage
- Success rate

**Quality (Manual Review):**
- Did it answer the question?
- Used relevant KB docs?
- Appropriate tone for intent?
- Clear call-to-action?
- Professional formatting?

**Retrieval Accuracy:**
- Did triage predict correct intent?
- Were suggested KB tags relevant?
- Did response use suggested doc types?

## Running the Test

```bash
# Test for specific client
python backend/scripts/ab_test_agent_systems.py --client pi-lit

# Custom output file
python backend/scripts/ab_test_agent_systems.py --client pi-lit --output pilit_ab_test.json
```

## Results Format

```json
{
  "client_slug": "pi-lit",
  "test_date": "2025-12-28T...",
  "total_queries": 8,
  "results": [
    {
      "query": "What does your company do?",
      "expected_intent": "MORE_INFO",
      "single_agent": {
        "success": true,
        "latency": 1.23,
        "response": "...",
        "usage": {"total_tokens": 450}
      },
      "hybrid_system": {
        "success": true,
        "latency": 1.45,
        "triage_latency": 0.15,
        "response_latency": 1.30,
        "response": "...",
        "triage_result": {
          "intent": "MORE_INFO",
          "kb_tags": ["about", "services_products"]
        },
        "usage": {"total_tokens": 480}
      }
    }
  ],
  "summary": {
    "single_agent": {
      "success_rate": 1.0,
      "avg_latency": 1.25,
      "total_tokens": 3600
    },
    "hybrid_system": {
      "success_rate": 1.0,
      "avg_latency": 1.48,
      "avg_triage_latency": 0.18,
      "avg_response_latency": 1.30,
      "total_tokens": 3850
    }
  }
}
```

## Analysis Checklist

After running the test, review:

### 1. Performance
- [ ] Is hybrid latency acceptable? (<2s total)
- [ ] What's the latency overhead? (<500ms ideal)
- [ ] Token usage increase? (<15% ideal)

### 2. Response Quality
For each query pair, compare:
- [ ] Accuracy: Did both answer correctly?
- [ ] Relevance: Which used better KB docs?
- [ ] Tone: Which matched intent better?
- [ ] Format: Which was clearer/more actionable?
- [ ] CTAs: Which had better next steps?

### 3. Triage Accuracy
- [ ] Intent detection accuracy? (>80% target)
- [ ] KB tag relevance? (manual check)
- [ ] False positives/negatives?

### 4. Edge Cases
- [ ] Ambiguous queries
- [ ] Multi-intent queries
- [ ] Out-of-scope queries
- [ ] Error handling

## Decision Criteria

**Choose Hybrid System if:**
- ✅ Response quality significantly better (>20% improvement)
- ✅ Latency overhead acceptable (<500ms)
- ✅ Triage accuracy high (>80%)
- ✅ Worth the additional complexity

**Stick with Single Agent if:**
- ✅ Quality improvement marginal (<10%)
- ✅ Latency overhead too high (>1s)
- ✅ Triage adds noise/confusion
- ✅ Simpler is better for maintenance

## Next Steps

### If Hybrid Wins:
1. Create actual triage agent in DigitalOcean
2. Update inbox-manager-v2 system prompt
3. Update query.py to orchestrate both agents
4. Deploy to staging for real-world testing
5. Monitor production metrics for 1 week
6. Full rollout if successful

### If Single Agent Wins:
1. Enhance current inbox-manager prompt
2. Add structured thinking workflow
3. Improve KB tag usage
4. Focus on response formatting

## Current Status

- [x] Created triage agent template
- [x] Created inbox-manager-v2 template
- [x] Built A/B test script
- [ ] Run test on pilot client
- [ ] Manual quality review
- [ ] Make decision
- [ ] Implement winner

## Notes

- Currently using simulated triage (rule-based)
- Need to create actual triage agent for production
- Consider caching triage results for follow-up questions
- Could add parallel testing (3+ responses, pick best)

