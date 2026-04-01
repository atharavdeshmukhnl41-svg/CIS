function renderGraph(nodesData, edgesData) {
 
  const container = document.getElementById("graph");
 
  if (!container) {
    console.log("Graph container not found");
    return;
  }
 
  if (!nodesData || nodesData.length === 0) {
    container.innerHTML = "No topology data";
    return;
  }
 
  const nodes = new vis.DataSet(
    nodesData.map(n => ({
      id: n.id,
      label: n.label || "Node",
      group: n.group
    }))
  );
 
  const edges = new vis.DataSet(
    edgesData.map(e => ({
      from: e.from,
      to: e.to,
      label: e.label,
      arrows: "to"
    }))
  );
 
  const options = {
    nodes: {
      shape: "dot",
      size: 15,
      font: { color: "#fff" }
    },
    edges: {
      font: { color: "#fff" },
      color: "#94a3b8"
    },
    groups: {
      VM: { color: "#22c55e" },
      NSG: { color: "#ef4444" },
      NIC: { color: "#3b82f6" },
      RULE: { color: "#f59e0b" }
    },
    physics: {
      enabled: true
    }
  };
 
  new vis.Network(container, { nodes, edges }, options);
}