# Nomos vNext Implementation Analysis and Proposal

## Current Issues Identified

### 1. Tool Execution and Context Handling
- **Problem**: The example manually feeds tool results back via `orch.input()`, but the orchestrator already handles this internally, leading to double processing.
- **Issue**: Context from tool results and transitions is not properly maintained across decisions.
- **Root Cause**: Example code assumes manual orchestration instead of letting the runtime handle multi-turn conversations.

### 2. Transition Logic
- **Problem**: LLM does not output `MOVE` actions despite available routes and conditions.
- **Issue**: Prompt instructs to "follow node instructions" but also "use MOVE if conditions met", creating confusion.
- **Root Cause**: Node prompts are too specific (e.g., "Greet the customer...") preventing recognition of transition conditions.

### 3. Decision Parsing
- **Problem**: Uses text generation + JSON parsing instead of structured outputs.
- **Issue**: Error-prone JSON parsing from streaming text.
- **Root Cause**: Not leveraging OpenAI's structured outputs (beta.chat.completions.parse).

### 4. Tool Modeling
- **Problem**: Tools are converted to Pydantic models but not used in structured decisions.
- **Issue**: Tool calls are parsed from text instead of validated schemas.
- **Root Cause**: Lack of proper ToolCall models in decision schema.

## Analysis of Old Implementation (.old/)

### Key Differences
1. **Structured Outputs**: Uses `client.beta.chat.completions.parse()` with Pydantic models for decisions.
2. **Decision Model**:
   ```python
   class Decision(BaseModel):
       reasoning: List[str]
       action: Action  # Enum: MOVE, RESPOND, TOOL_CALL
       response: Optional[str]
       tool_call: Optional[ToolCall]
       step_id: Optional[str]
   ```
3. **Tool Models**: Tools are full Pydantic models with argument schemas.
4. **Runtime Logic**: LLM outputs structured Decision, runtime executes based on action.
5. **Prompt Structure**: System includes step description, routes, tools, examples; User includes formatted history.

### Advantages of Old Approach
- **Type Safety**: Decisions are validated Pydantic models.
- **Reliability**: No JSON parsing errors.
- **Clarity**: Clear separation of LLM decision vs runtime execution.
- **Tool Validation**: Tool arguments validated against schemas.

## Proposed Fixes for vNext

### Phase 1: Fix Current Issues
1. **Remove Manual Tool Result Feeding**: Update example to let orchestrator handle internally.
2. **Fix Prompt Logic**: Change node prompts to be decision-oriented rather than action-oriented.
3. **Improve Transition Detection**: Make routes primary, node instructions secondary.

### Phase 2: Adopt Structured Outputs
1. **Define Decision Schema**:
   ```python
   class Decision(BaseModel):
       reasoning: List[str]
       action: Literal["RESPOND", "TOOL_CALL", "MOVE"]
       response: Optional[str] = None
       tool_call: Optional[ToolCall] = None
       step_id: Optional[str] = None
   ```

2. **Update OpenAI Provider**:
   - Add `get_structured_decision()` method using `client.beta.chat.completions.parse()`
   - Modify `stream_decision()` to use structured parsing when schema provided
   - Fall back to text parsing for compatibility

3. **Update Orchestrator**:
   - Handle structured Decision objects
   - Validate tool calls against schemas
   - Ensure proper context passing

### Phase 3: Improve Tool Modeling
1. **Enhance Tool Runner**: Ensure all tools have proper Pydantic schemas.
2. **Tool Call Validation**: Validate tool arguments before execution.
3. **Error Handling**: Better error messages for invalid tool calls.

### Phase 4: Update Examples and Tests
1. **Fix Barista Example**: Remove manual orchestration, let runtime handle.
2. **Add Tests**: Test transitions, tool calls, context passing.
3. **Documentation**: Update guides to reflect structured approach.

## Implementation Plan

### Immediate Actions (Phase 1)
- [ ] Remove manual `orch.input()` calls in example stream loops
- [ ] Update node prompts to be more decision-focused
- [ ] Add reasoning to decision schema
- [ ] Test transition logic

### Short Term (Phase 2)
- [ ] Implement structured outputs in OpenAI provider
- [ ] Update orchestrator to handle Decision models
- [ ] Add tool validation
- [ ] Update tests

### Long Term (Phase 3-4)
- [ ] Refactor all providers to use structured outputs
- [ ] Improve error handling and observability
- [ ] Update documentation and examples

## Benefits of Proposed Changes
1. **Reliability**: Structured outputs eliminate parsing errors.
2. **Type Safety**: Pydantic models ensure data integrity.
3. **Maintainability**: Clear separation of concerns.
4. **Performance**: Better error handling and validation.
5. **Compatibility**: Maintains streaming for tokens while using structured decisions.

## Risks and Mitigations
1. **OpenAI API Changes**: Structured outputs are in beta; monitor for changes.
2. **Breaking Changes**: Ensure backward compatibility during transition.
3. **Performance**: Structured parsing may be slower; optimize where needed.

## Conclusion
The current vNext implementation has fundamental issues with decision parsing and orchestration logic. By adopting the structured outputs approach from the old implementation, we can achieve reliable, type-safe agent execution while maintaining the streaming and async benefits of vNext.</content>
<parameter name="filePath">/Users/chandralegend/Documents/dowhiledev/nomos/PROPOSAL.md
