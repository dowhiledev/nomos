import dagre from 'dagre';
import type { Node, Edge } from '@xyflow/react';

// Fixed node dimensions
const STEP_NODE_WIDTH = 280;
const STEP_NODE_HEIGHT = 140;
const TOOL_NODE_WIDTH = 200;
const TOOL_NODE_HEIGHT = 100;

// Grid settings
const GRID_SIZE = 20;

// Utility function to snap position to grid
function snapToGrid(position: { x: number; y: number }): { x: number; y: number } {
  return {
    x: Math.round(position.x / GRID_SIZE) * GRID_SIZE,
    y: Math.round(position.y / GRID_SIZE) * GRID_SIZE,
  };
}

export function autoArrangeNodes(nodes: Node[], edges: Edge[]): Node[] {
  // Separate different node types
  const ungroupedStepNodes = nodes.filter(node => node.type === 'step' && !node.parentId);
  const toolNodes = nodes.filter(node => node.type === 'tool');
  const groupNodes = nodes.filter(node => node.type === 'group');
  const groupedStepNodes = nodes.filter(node => node.type === 'step' && node.parentId);

  // Create the main graph for ungrouped step nodes only
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // Configure the layout with generous spacing for clear visibility
  dagreGraph.setGraph({
    rankdir: 'TB',  // Top to bottom
    align: 'UL',    // Upper left alignment
    nodesep: 200,   // Much larger horizontal spacing between nodes
    ranksep: 250,   // Much larger vertical spacing between ranks
    marginx: 100,   // Larger margins
    marginy: 100,
  });

  // Add ungrouped step nodes to the graph
  ungroupedStepNodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: STEP_NODE_WIDTH,
      height: STEP_NODE_HEIGHT
    });
  });

  // Add group nodes as "super nodes" to the layout graph
  // This allows dagre to consider groups in the overall flow layout
  groupNodes.forEach((groupNode) => {
    const groupWidth = groupNode.style?.width as number || 400;
    const groupHeight = groupNode.style?.height as number || 300;

    dagreGraph.setNode(groupNode.id, {
      width: groupWidth,
      height: groupHeight
    });
  });

  // Add route edges to the graph including mixed scenarios
  edges.forEach((edge) => {
    if (edge.type === 'route') {
      // Find if source/target are grouped nodes
      const sourceGroupedNode = groupedStepNodes.find(n => n.id === edge.source);
      const targetGroupedNode = groupedStepNodes.find(n => n.id === edge.target);

      let sourceId = edge.source;
      let targetId = edge.target;

      // If source is grouped, use the parent group as the source
      if (sourceGroupedNode && sourceGroupedNode.parentId) {
        sourceId = sourceGroupedNode.parentId;
      }

      // If target is grouped, use the parent group as the target
      if (targetGroupedNode && targetGroupedNode.parentId) {
        targetId = targetGroupedNode.parentId;
      }

      // Add edge to layout graph if both endpoints exist in our graph
      const sourceExists = dagreGraph.hasNode(sourceId);
      const targetExists = dagreGraph.hasNode(targetId);

      if (sourceExists && targetExists && sourceId !== targetId) {
        dagreGraph.setEdge(sourceId, targetId);
      }
    }
  });

  // Run the layout algorithm
  dagre.layout(dagreGraph);

  // Apply the new positions to ungrouped step nodes from dagre layout
  const arrangedUngroupedStepNodes = ungroupedStepNodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);

    // Dagre centers the nodes, so we need to adjust for top-left positioning
    const position = {
      x: nodeWithPosition.x - STEP_NODE_WIDTH / 2,
      y: nodeWithPosition.y - STEP_NODE_HEIGHT / 2,
    };

    return {
      ...node,
      position: snapToGrid(position),
    };
  });

  // Apply the new positions to group nodes from dagre layout
  const arrangedGroupNodes = groupNodes.map((groupNode) => {
    if (dagreGraph.hasNode(groupNode.id)) {
      const nodeWithPosition = dagreGraph.node(groupNode.id);
      const groupWidth = groupNode.style?.width as number || 400;
      const groupHeight = groupNode.style?.height as number || 300;

      // Dagre centers the nodes, so we need to adjust for top-left positioning
      const position = {
        x: nodeWithPosition.x - groupWidth / 2,
        y: nodeWithPosition.y - groupHeight / 2,
      };

      return {
        ...groupNode,
        position: snapToGrid(position),
      };
    }
    return groupNode;
  });

  // Now optimize group bounds based on child nodes using the NEW positions from dagre
  const groupOptimizations = arrangedGroupNodes.map(groupNode => {
    const childNodes = groupedStepNodes.filter(child => child.parentId === groupNode.id);
    if (childNodes.length > 0) {
      const bounds = calculateOptimalGroupBounds(groupNode, childNodes);
      return {
        optimizedGroup: {
          ...groupNode,
          position: bounds.position,
          style: {
            ...groupNode.style,
            width: bounds.size.width,
            height: bounds.size.height,
          },
        },
        childAdjustments: bounds.childAdjustments
      };
    }
    return {
      optimizedGroup: groupNode,
      childAdjustments: []
    };
  });

  const optimizedGroupNodes = groupOptimizations.map(opt => opt.optimizedGroup);

  // Calculate optimized group boundaries for collision detection using the new positions
  const groupBoundaries = optimizedGroupNodes.map(group => ({
    minX: group.position.x,
    minY: group.position.y,
    maxX: group.position.x + (group.style?.width as number || 400),
    maxY: group.position.y + (group.style?.height as number || 300),
  }));

  // Utility function to check if a position overlaps with any group
  const isPositionInsideGroup = (x: number, y: number, width: number, height: number): boolean => {
    return groupBoundaries.some(boundary => {
      const nodeRight = x + width;
      const nodeBottom = y + height;

      return !(x >= boundary.maxX || nodeRight <= boundary.minX || y >= boundary.maxY || nodeBottom <= boundary.minY);
    });
  };

  // Apply child position adjustments based on group optimizations BEFORE tool positioning
  const adjustedGroupedStepNodes = groupedStepNodes.map(child => {
    const parentOptimization = groupOptimizations.find(opt =>
      opt.childAdjustments.some(adj => adj.id === child.id)
    );

    if (parentOptimization) {
      const adjustment = parentOptimization.childAdjustments.find(adj => adj.id === child.id);
      if (adjustment) {
        return {
          ...child,
          position: adjustment.newRelativePosition,
        };
      }
    }

    return child;
  });

  // Create a combined list of all step nodes for tool positioning reference
  const allStepNodesWithPositions = [
    ...arrangedUngroupedStepNodes,
    ...adjustedGroupedStepNodes
  ];

  // Position tool nodes intelligently - aim for natural placement near connected nodes
  let toolNodeOffsetIndex = 0;

  // Calculate a more natural tool positioning strategy
  // Instead of pushing all tools to the far right, try to place them near their connected nodes first
  const mainFlowBounds = {
    minX: Math.min(...arrangedUngroupedStepNodes.map(n => n.position.x)),
    maxX: Math.max(...arrangedUngroupedStepNodes.map(n => n.position.x + STEP_NODE_WIDTH)),
    minY: Math.min(...arrangedUngroupedStepNodes.map(n => n.position.y)),
    maxY: Math.max(...arrangedUngroupedStepNodes.map(n => n.position.y + STEP_NODE_HEIGHT)),
  };

  // For disconnected tools, place them in a more natural location - either to the right of main flow
  // or below it, whichever gives better spacing
  const fallbackToolAreaX = mainFlowBounds.maxX + 40; // Much closer to main flow
  const fallbackToolAreaY = mainFlowBounds.minY;


  const arrangedToolNodes = toolNodes.map((toolNode) => {
    // Find all step nodes that connect to this tool
    const connectedStepEdges = edges.filter(
      (edge) => edge.type === 'tool' && edge.target === toolNode.id
    );

    if (connectedStepEdges.length === 0) {
      // No connections - place in a compact area near the main flow
      let position: { x: number; y: number };
      let attempts = 0;

      // Try positions progressively further from main flow
      do {
        const col = Math.floor(toolNodeOffsetIndex / 3);
        const row = toolNodeOffsetIndex % 3;

        position = {
          x: fallbackToolAreaX + (col * (TOOL_NODE_WIDTH + 40)),
          y: fallbackToolAreaY + (row * (TOOL_NODE_HEIGHT + 40))
        };

        if (isPositionInsideGroup(position.x, position.y, TOOL_NODE_WIDTH, TOOL_NODE_HEIGHT)) {
          // Try next position or move further right
          toolNodeOffsetIndex++;
          attempts++;
          if (attempts > 10) {
            // Safety: place well clear of everything
            position = {
              x: fallbackToolAreaX + 200 + (attempts * 30),
              y: fallbackToolAreaY + (row * (TOOL_NODE_HEIGHT + 40))
            };
            break;
          }
        } else {
          break;
        }
      } while (true);

      toolNodeOffsetIndex++;
      return {
        ...toolNode,
        position: snapToGrid(position),
      };
    }

    // Connected tool - try to place it near the connected step node
    const primaryStepEdge = connectedStepEdges[0];

    // Search for the connected step node in ALL step nodes (ungrouped and grouped)
    let primaryStepNode = allStepNodesWithPositions.find((n: Node) => n.id === primaryStepEdge.source);

    if (!primaryStepNode) {
      // Fallback to disconnected logic
      let position = {
        x: fallbackToolAreaX + (toolNodeOffsetIndex * 40),
        y: fallbackToolAreaY + 100
      };

      // Quick check for group collision
      if (isPositionInsideGroup(position.x, position.y, TOOL_NODE_WIDTH, TOOL_NODE_HEIGHT)) {
        position = {
          x: fallbackToolAreaX + 200,
          y: fallbackToolAreaY + (toolNodeOffsetIndex * 60)
        };
      }

      toolNodeOffsetIndex++;
      return {
        ...toolNode,
        position: snapToGrid(position),
      };
    }

    // Smart positioning: try to place tool near its connected step node
    let position: { x: number; y: number };
    const stepNode = primaryStepNode;

    // Calculate the absolute position of the step node
    // If it's a grouped node, we need to add the group position to its relative position
    let stepAbsolutePosition = { ...stepNode.position };
    if (stepNode.parentId) {
      const parentGroup = optimizedGroupNodes.find(g => g.id === stepNode.parentId);
      if (parentGroup) {
        stepAbsolutePosition = {
          x: parentGroup.position.x + stepNode.position.x,
          y: parentGroup.position.y + stepNode.position.y,
        };
      }
    }

    // Try multiple natural positions around the connected step node with increased spacing
    const candidatePositions = [
      // Right of the step node (preferred) - increased spacing for better visibility
      { x: stepAbsolutePosition.x + STEP_NODE_WIDTH + 100, y: stepAbsolutePosition.y },
      // Below the step node - increased spacing
      { x: stepAbsolutePosition.x, y: stepAbsolutePosition.y + STEP_NODE_HEIGHT + 100 },
      // Above the step node - increased spacing
      { x: stepAbsolutePosition.x, y: stepAbsolutePosition.y - TOOL_NODE_HEIGHT - 100 },
      // Further right - increased spacing
      { x: stepAbsolutePosition.x + STEP_NODE_WIDTH + 150, y: stepAbsolutePosition.y },
    ];

    // Find the first position that doesn't conflict with groups
    position = candidatePositions.find(pos =>
      !isPositionInsideGroup(pos.x, pos.y, TOOL_NODE_WIDTH, TOOL_NODE_HEIGHT)
    ) || {
      // Fallback: place in the general tool area
      x: fallbackToolAreaX + 50,
      y: fallbackToolAreaY + (toolNodeOffsetIndex * (TOOL_NODE_HEIGHT + 30))
    };

    toolNodeOffsetIndex++;
    return {
      ...toolNode,
      position: snapToGrid(position),
    };
  });

  // Final pass: resolve any tool node overlaps with a more natural approach
  const finalToolNodes = arrangedToolNodes.map((toolNode, index) => {
    // Check for overlaps with previously positioned tool nodes
    const overlappingNodes = arrangedToolNodes.slice(0, index).filter((otherNode) => {
      const xOverlap = Math.abs(toolNode.position.x - otherNode.position.x) < TOOL_NODE_WIDTH + 20;
      const yOverlap = Math.abs(toolNode.position.y - otherNode.position.y) < TOOL_NODE_HEIGHT + 20;
      return xOverlap && yOverlap;
    });

    if (overlappingNodes.length > 0) {
      // Instead of just moving down, try to find a nearby open spot
      let adjustedPosition = { ...toolNode.position };

      // Try small adjustments first (right, down, diagonal)
      const adjustmentAttempts = [
        { x: adjustedPosition.x + TOOL_NODE_WIDTH + 30, y: adjustedPosition.y },
        { x: adjustedPosition.x, y: adjustedPosition.y + TOOL_NODE_HEIGHT + 30 },
        { x: adjustedPosition.x + TOOL_NODE_WIDTH + 30, y: adjustedPosition.y + TOOL_NODE_HEIGHT + 30 },
        { x: adjustedPosition.x, y: adjustedPosition.y + (overlappingNodes.length * (TOOL_NODE_HEIGHT + 40)) },
      ];

      // Find first position that doesn't overlap with groups and other tools
      for (const attempt of adjustmentAttempts) {
        const wouldOverlapGroup = isPositionInsideGroup(attempt.x, attempt.y, TOOL_NODE_WIDTH, TOOL_NODE_HEIGHT);
        const wouldOverlapTool = arrangedToolNodes.slice(0, index).some(otherNode => {
          const xOverlap = Math.abs(attempt.x - otherNode.position.x) < TOOL_NODE_WIDTH + 20;
          const yOverlap = Math.abs(attempt.y - otherNode.position.y) < TOOL_NODE_HEIGHT + 20;
          return xOverlap && yOverlap;
        });

        if (!wouldOverlapGroup && !wouldOverlapTool) {
          adjustedPosition = attempt;
          break;
        }
      }

      return {
        ...toolNode,
        position: snapToGrid(adjustedPosition),
      };
    }

    return toolNode;
  });

  // Combine all nodes: arranged ungrouped steps, arranged tools, optimized groups and adjusted grouped steps
  return [...arrangedUngroupedStepNodes, ...finalToolNodes, ...optimizedGroupNodes, ...adjustedGroupedStepNodes];
}

// Utility function to calculate optimal group bounds based on child nodes
export function calculateOptimalGroupBounds(groupNode: Node, childNodes: Node[]) {
  if (childNodes.length === 0) {
    return {
      position: groupNode.position,
      size: { width: 400, height: 300 }, // Default minimum size
      childAdjustments: []
    };
  }

  // Calculate absolute positions of child nodes
  const childAbsolutePositions = childNodes.map(child => ({
    id: child.id,
    x: groupNode.position.x + child.position.x,
    y: groupNode.position.y + child.position.y,
    width: child.type === 'step' ? STEP_NODE_WIDTH : TOOL_NODE_WIDTH,
    height: child.type === 'step' ? STEP_NODE_HEIGHT : TOOL_NODE_HEIGHT,
    originalRelativePosition: child.position,
  }));

  const padding = 60; // Consistent padding around child nodes
  const minX = Math.min(...childAbsolutePositions.map(pos => pos.x));
  const minY = Math.min(...childAbsolutePositions.map(pos => pos.y));
  const maxX = Math.max(...childAbsolutePositions.map(pos => pos.x + pos.width));
  const maxY = Math.max(...childAbsolutePositions.map(pos => pos.y + pos.height));

  // Calculate optimal bounds with padding
  const optimalPosition = {
    x: minX - padding,
    y: minY - padding
  };

  const optimalSize = {
    width: Math.max(400, (maxX - minX) + (padding * 2)), // Minimum width of 400
    height: Math.max(300, (maxY - minY) + (padding * 2)) // Minimum height of 300
  };

  // Calculate position delta for child node adjustments
  const deltaX = optimalPosition.x - groupNode.position.x;
  const deltaY = optimalPosition.y - groupNode.position.y;

  // Calculate child position adjustments if group position changes
  const childAdjustments = childAbsolutePositions.map(child => ({
    id: child.id,
    newRelativePosition: {
      x: child.originalRelativePosition.x - deltaX,
      y: child.originalRelativePosition.y - deltaY,
    }
  }));

  return {
    position: optimalPosition,
    size: optimalSize,
    childAdjustments
  };
}
