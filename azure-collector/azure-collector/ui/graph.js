async function loadGraph() {
 
    const container = document.getElementById("graph");
 
    container.innerHTML = "Loading graph...";
 
    try {
 
        const res = await fetch("http://127.0.0.1:9000/topology");
        const data = await res.json();
 
        if (data.error) {
            container.innerHTML = "❌ " + data.error;
            return;
        }
 
        // ✅ FIX: vis format
        const nodes = new vis.DataSet(data.nodes);
        const edges = new vis.DataSet(data.edges);
 
        const options = {
            layout: {
                improvedLayout: true
            },
            physics: {
                enabled: true,
                stabilization: false
            },
            nodes: {
                shape: "dot",
                size: 18,
                font: {
                    size: 14,
                    color: "#ffffff"
                }
            },
            edges: {
                arrows: "to",
                font: {
                    align: "middle",
                    size: 10
                }
            },
            groups: {
                VM: { color: "#22c55e" },
                NSG: { color: "#ef4444" },
                NIC: { color: "#3b82f6" },
                Database: { color: "#f59e0b" }
            }
        };
 
        new vis.Network(container, { nodes, edges }, options);
 
    } catch (err) {
        container.innerHTML = "❌ Graph load failed: " + err;
    }
}