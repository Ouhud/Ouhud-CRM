let nodes = [];
let counter = 1;
const area = document.getElementById("nodes_area");

function addNode(type) {
    const id = "node_" + counter++;
    const div = document.createElement("div");

    div.className = "node";
    div.style.top = "40px";
    div.style.left = "40px";

    div.innerHTML = `<strong>${type.toUpperCase()}</strong><br>ID: ${id}`;

    let offsetX = 0, offsetY = 0;

    div.onmousedown = (e) => {
        offsetX = e.offsetX;
        offsetY = e.offsetY;

        document.onmousemove = (ev) => {
            div.style.left = (ev.pageX - area.offsetLeft - offsetX) + "px";
            div.style.top = (ev.pageY - area.offsetTop - offsetY) + "px";
        };

        document.onmouseup = () => {
            document.onmousemove = null;
        };
    };

    area.appendChild(div);

    nodes.push({
        id: id,
        type: type,
        x: 40,
        y: 40
    });
}

function saveWorkflow() {
    document.getElementById("json_data").value = JSON.stringify(nodes);
    document.getElementById("wf_name").value = prompt("Name des Workflows:");
    document.getElementById("wf_desc").value = prompt("Beschreibung:");
    document.getElementById("save_form").submit();
}
