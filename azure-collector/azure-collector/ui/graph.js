function renderGraph(nodesData, edgesData, onHoverNode) {

  const container = document.getElementById("topologyGraph");

  if (!container) {
    console.log("Graph container not found");
    return;
  }

  if (!nodesData || nodesData.length === 0) {
    container.innerHTML = '<div class="empty-state"><i class="fas fa-project-diagram"></i><h4>No Topology Data</h4><p>Unable to load infrastructure topology</p></div>';
    return;
  }

  // Clear any existing content
  container.innerHTML = '';

  // Process nodes with enhanced status information
  const nodes = new vis.DataSet(
    nodesData.map(n => {
      const nodeConfig = {
        id: n.id,
        label: n.label,
        group: n.group,
        title: createNodeTooltip(n), // Enhanced tooltip
        font: {
          color: "#f8fafc",
          size: 12,
          face: 'arial'
        },
        borderWidth: 3,
        shadow: true
      };

      // Set colors based on status
      if (n.status === 'error') {
        nodeConfig.color = {
          background: '#ef4444',
          border: '#dc2626',
          highlight: { background: '#dc2626', border: '#b91c1c' }
        };
        nodeConfig.label += ' ❌'; // Add error indicator
      } else if (n.status === 'warning') {
        nodeConfig.color = {
          background: '#f59e0b',
          border: '#d97706',
          highlight: { background: '#d97706', border: '#b45309' }
        };
        nodeConfig.label += ' ⚠️'; // Add warning indicator
      } else {
        // Use default colors based on group
        nodeConfig.color = getNodeColor(n.group);
      }

      return nodeConfig;
    })
  );

  // Process edges with enhanced styling
  const edges = new vis.DataSet(
    edgesData.map(e => ({
      from: e.from,
      to: e.to,
      label: e.label,
      title: e.description || e.label, // Enhanced tooltip
      color: {
        color: e.color || '#64748b',
        highlight: '#3b82f6'
      },
      arrows: {
        to: {
          enabled: true,
          scaleFactor: 0.8
        }
      },
      font: {
        align: 'middle',
        size: 10,
        color: '#cbd5e1'
      },
      smooth: {
        enabled: true,
        type: 'continuous'
      },
      width: 2
    }))
  );

  const options = {
    nodes: {
      shape: "dot",
      size: 20,
      font: {
        color: "#f8fafc",
        size: 12,
        face: 'arial'
      },
      borderWidth: 3,
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.3)',
        size: 5
      }
    },
    edges: {
      font: {
        color: "#cbd5e1",
        size: 10,
        align: 'middle'
      },
      arrows: {
        to: {
          enabled: true,
          scaleFactor: 0.8
        }
      },
      smooth: {
        enabled: true,
        type: "continuous"
      },
      width: 2
    },
    groups: {
      VM: {
        color: {
          background: "#10b981",
          border: "#059669",
          highlight: { background: "#059669", border: "#047857" }
        },
        shape: 'square'
      },
      NSG: {
        color: {
          background: "#ef4444",
          border: "#dc2626",
          highlight: { background: "#dc2626", border: "#b91c1c" }
        },
        shape: 'diamond'
      },
      NIC: {
        color: {
          background: "#3b82f6",
          border: "#2563eb",
          highlight: { background: "#2563eb", border: "#1d4ed8" }
        },
        shape: 'dot'
      },
      RULE: {
        color: {
          background: "#f59e0b",
          border: "#d97706",
          highlight: { background: "#d97706", border: "#b45309" }
        },
        shape: 'triangle'
      },
      LoadBalancer: {
        color: {
          background: "#8b5cf6",
          border: "#7c3aed",
          highlight: { background: "#7c3aed", border: "#6d28d9" }
        },
        shape: 'hexagon'
      },
      LB: {
        color: {
          background: "#8b5cf6",
          border: "#7c3aed",
          highlight: { background: "#7c3aed", border: "#6d28d9" }
        },
        shape: 'hexagon'
      },
      PublicIP: {
        color: {
          background: "#06b6d4",
          border: "#0891b2",
          highlight: { background: "#0891b2", border: "#0e7490" }
        },
        shape: 'dot'
      },
      RouteTable: {
        color: {
          background: "#ec4899",
          border: "#db2777",
          highlight: { background: "#db2777", border: "#be185d" }
        },
        shape: 'box'
      },
      Metrics: {
        color: {
          background: "#64748b",
          border: "#475569",
          highlight: { background: "#475569", border: "#334155" }
        },
        shape: 'circle'
      }
    },
    physics: {
      enabled: true,
      barnesHut: {
        gravitationalConstant: -3000,
        centralGravity: 0.1,
        springLength: 150,
        springConstant: 0.03,
        damping: 0.09
      },
      stabilization: {
        enabled: true,
        iterations: 1000,
        updateInterval: 25
      }
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      zoomView: true,
      dragView: true
    },
    layout: {
      improvedLayout: true,
      hierarchical: {
        enabled: false
      }
    }
  };

  const network = new vis.Network(container, { nodes, edges }, options);

  // Add event listeners for better UX
  network.on("stabilizationProgress", function(params) {
    console.log('Graph stabilization:', Math.round(params.iterations / params.total * 100) + '%');
  });

  network.on("stabilizationIterationsDone", function() {
    console.log('Graph stabilization complete');
  });

  network.on("hoverNode", function(params) {
    const nodeId = params.node;
    const node = nodesData.find(n => n.id === nodeId);
    if (node) {
      if (node.status === 'error') {
        network.selectNodes([nodeId]);
      }
      if (typeof onHoverNode === 'function') {
        onHoverNode(node);
      }
    }
  });

  network.on("blurNode", function() {
    network.selectNodes([]);
    if (typeof onHoverNode === 'function') {
      onHoverNode(null);
    }
  });

  return network;
}

function getNodeColor(group) {
  const colors = {
    VM: { background: "#10b981", border: "#059669", highlight: { background: "#059669", border: "#047857" } },
    NSG: { background: "#ef4444", border: "#dc2626", highlight: { background: "#dc2626", border: "#b91c1c" } },
    NIC: { background: "#3b82f6", border: "#2563eb", highlight: { background: "#2563eb", border: "#1d4ed8" } },
    RULE: { background: "#f59e0b", border: "#d97706", highlight: { background: "#d97706", border: "#b45309" } },
    LB: { background: "#8b5cf6", border: "#7c3aed", highlight: { background: "#7c3aed", border: "#6d28d9" } },
    PublicIP: { background: "#06b6d4", border: "#0891b2", highlight: { background: "#0891b2", border: "#0e7490" } },
    RouteTable: { background: "#ec4899", border: "#db2777", highlight: { background: "#db2777", border: "#be185d" } },
    Metrics: { background: "#64748b", border: "#475569", highlight: { background: "#475569", border: "#334155" } }
  };

  return colors[group] || { background: "#64748b", border: "#475569", highlight: { background: "#475569", border: "#334155" } };
}

function createNodeTooltip(node) {
  const safeValue = value => (value === null || value === undefined || value === '') ? 'Unknown' : value;
  const lines = [];
  lines.push(`${safeValue(node.label)} (${safeValue(node.group)})`);

  if (node.properties) {
    if ('resource_group' in node.properties) lines.push(`Resource Group: ${safeValue(node.properties.resource_group)}`);
    if ('location' in node.properties) lines.push(`Location: ${safeValue(node.properties.location)}`);
    if ('state' in node.properties) lines.push(`State: ${safeValue(node.properties.state)}`);
    if ('type' in node.properties) lines.push(`Type: ${safeValue(node.properties.type)}`);
    if ('cpu' in node.properties) lines.push(`CPU: ${safeValue(node.properties.cpu)}%`);
  }

  if (node.status) {
    lines.push(`Status: ${safeValue(node.status)}`);
  }

  return lines.join('\n');
}

