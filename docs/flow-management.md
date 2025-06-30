# Flow Management

NOMOS provides advanced flow management capabilities that allow you to organize related steps into logical groups with shared context and components. Flows are perfect for complex workflows that require stateful interactions, context preservation, and intelligent transitions between different parts of your agent's behavior.

## What are Flows?

Flows are containers that group related steps together and provide:

- **Shared Memory**: Each flow maintains its own context that persists across steps within the flow
- **Component Management**: Flows can have dedicated components like memory systems, specialized tools, or custom handlers
- **Context Transfer**: When transitioning between flows, context is intelligently summarized and passed along
- **Entry/Exit Points**: Define which steps can enter or exit a flow for better control flow management

## Flow Configuration

You can define flows in your YAML configuration:

```yaml
# Basic agent configuration
name: advanced-assistant
persona: A helpful assistant with specialized workflows
start_step_id: greeting

steps:
  - step_id: greeting
    description: Greet the user and understand their needs
    routes:
      - target: order_taking
        condition: User wants to place an order
      - target: customer_support
        condition: User needs help or support

  - step_id: order_taking
    description: Handle order details and preferences
    available_tools:
      - get_menu_items
      - add_to_cart
    routes:
      - target: order_confirmation
        condition: Order is complete

  - step_id: order_confirmation
    description: Confirm order details and process payment
    available_tools:
      - calculate_total
      - process_payment
    routes:
      - target: farewell
        condition: Order is confirmed

  - step_id: customer_support
    description: Handle customer inquiries and issues
    available_tools:
      - search_knowledge_base
      - escalate_to_human
    routes:
      - target: farewell
        condition: Issue is resolved

  - step_id: farewell
    description: Thank the user and end the conversation

# Enhanced flows configuration
flows:
  - flow_id: order_management
    description: "Complete order processing workflow"
    enters:
      - order_taking
    exits:
      - order_confirmation
      - farewell
    components:
      memory:
        llm:
          provider: openai
          model: gpt-4o-mini
        retriever:
          method: embedding
          kwargs:
            k: 5
    metadata:
      max_context_size: 50
      summary_threshold: 20

  - flow_id: support_workflow
    description: "Customer support and issue resolution"
    enters:
      - customer_support
    exits:
      - farewell
    components:
      memory:
        llm:
          provider: openai
          model: gpt-4o-mini
        retriever:
          method: embedding
```

## Flow Memory and Context

Each flow can have its own memory system that:

- **Preserves Context**: Maintains conversation history and important details within the flow
- **Intelligent Retrieval**: Uses BM25 or other retrieval methods to find relevant information
- **Context Summarization**: Automatically summarizes context when exiting a flow
- **Cross-Flow Transfer**: Passes summarized context when transitioning between flows

## Flow Benefits

1. **Organized Architecture**: Keep related functionality grouped together
2. **Context Awareness**: Maintain relevant information throughout related interactions
3. **Scalable Design**: Easily extend your agent with new flows without affecting existing ones
4. **Memory Efficiency**: Each flow only maintains context relevant to its purpose
5. **Flexible Transitions**: Define precise entry and exit conditions for better control flow

## Example: Barista Agent with Flows

The barista example demonstrates flow usage for order management:

```yaml
flows:
  - flow_id: take_coffee_order
    description: "Complete coffee ordering process"
    enters:
      - take_coffee_order
    exits:
      - finalize_order
      - end
    components:
      memory:
        llm:
          provider: openai
          model: gpt-4o-mini
        retriever:
          method: embedding
          kwargs:
            k: 5
```

This flow ensures that all order-related context (customer preferences, cart contents, order history) is maintained throughout the ordering process and properly summarized when the order is complete.

## Advanced Flow Patterns

### Multi-Flow Applications

You can create sophisticated applications by combining multiple flows:

```yaml
flows:
  - flow_id: authentication
    description: "User login and verification"
    enters: [login]
    exits: [dashboard, main_menu]

  - flow_id: order_processing
    description: "Handle customer orders"
    enters: [order_taking]
    exits: [checkout, main_menu]

  - flow_id: customer_support
    description: "Handle customer inquiries"
    enters: [support_request]
    exits: [resolution, escalation]
```

### Flow Transitions

Flows automatically handle context transfer when users move between different workflows, ensuring seamless user experience while maintaining relevant information.
