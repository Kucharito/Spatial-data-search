const API_BASE_URL = "http://localhost:8000";
const map = L.map("map").setView([49.8209, 18.2625], 12);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const categorySelect = document.getElementById("category-select");
const kInput = document.getElementById("k-input");
const radiusInput = document.getElementById("radius-input");
const backendStatus = document.getElementById("backend-status");
const selectedCoords = document.getElementById("selected-coords");
const resultsBody = document.getElementById("results-body");
const resultsInfo = document.getElementById("results-info");

const markersLayer = L.layerGroup().addTo(map);
let selectedMarker = null;
let radiusCircle = null;
let currentPoint = null;

function formatDistance(place) {
  // Format distance for display in the results table.
  if (place.distance_m === undefined || place.distance_m === null) {
    return "-";
  }
  return Number(place.distance_m).toFixed(2);
}

function renderTable(places) {
  // Render the results table for the current place list.
  resultsBody.innerHTML = "";
  resultsInfo.textContent = `${places.length} rows`;

  if (places.length === 0) {
    const row = document.createElement("tr");
    row.className = "empty-row";
    row.innerHTML = '<td colspan="4">No results to display.</td>';
    resultsBody.appendChild(row);
    return;
  }

  for (const place of places) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${place.name}</td>
      <td>${place.category}</td>
      <td>${place.address || ""}</td>
      <td>${formatDistance(place)}</td>
    `;
    resultsBody.appendChild(row);
  }
}

function clearResultsLayers() {
  // Remove current markers and radius circle from the map.
  markersLayer.clearLayers();
  if (radiusCircle) {
    map.removeLayer(radiusCircle);
    radiusCircle = null;
  }
}

function drawPlaces(places) {
  // Draw place markers and popups for a new result set.
  clearResultsLayers();

  for (const place of places) {
    const marker = L.marker([place.latitude, place.longitude]);
    marker.bindPopup(`
      <strong>${place.name}</strong><br>
      Category: ${place.category}<br>
      Address: ${place.address || "-"}<br>
      Distance: ${formatDistance(place)} m
    `);
    marker.addTo(markersLayer);
  }
}

function setSelectedPoint(lat, lon) {
  // Store the selected point and display its marker.
  currentPoint = { lat, lon };
  selectedCoords.textContent = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;

  if (selectedMarker) {
    map.removeLayer(selectedMarker);
  }

  selectedMarker = L.marker([lat, lon], { title: "Selected point" }).addTo(map);
  selectedMarker.bindPopup("Selected search point").openPopup();
}

async function apiGet(path) {
  // Perform a GET request to the backend API.
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with ${response.status}`);
  }
  return response.json();
}

async function apiPost(path, payload) {
  // Perform a POST request to the backend API.
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with ${response.status}`);
  }

  return response.json();
}

function getCategoryQuery() {
  // Build the optional category filter query string.
  return categorySelect.value ? `&category=${encodeURIComponent(categorySelect.value)}` : "";
}

function requireSelectedPoint() {
  // Guard against queries without a selected map point.
  if (!currentPoint) {
    throw new Error("Select a point on the map first.");
  }
}

async function loadCategories() {
  // Fetch categories and populate the dropdown.
  const data = await apiGet("/categories");
  for (const category of data.categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categorySelect.appendChild(option);
  }
}

async function loadAllPlaces() {
  // Load and display all places (optionally filtered).
  const query = categorySelect.value ? `?category=${encodeURIComponent(categorySelect.value)}` : "";
  const places = await apiGet(`/places${query}`);
  drawPlaces(places);
  renderTable(places);
}

async function findNearestPlaces() {
  // Run nearest search for the selected point.
  requireSelectedPoint();
  const k = Number(kInput.value) || 5;
  const query = `/places/nearest?lat=${currentPoint.lat}&lon=${currentPoint.lon}&k=${k}${getCategoryQuery()}`;
  const places = await apiGet(query);
  drawPlaces(places);
  renderTable(places);
}

async function findWithinRadius() {
  // Run radius search for the selected point and draw the circle.
  requireSelectedPoint();
  const radius = Number(radiusInput.value) || 1000;
  const query = `/places/radius?lat=${currentPoint.lat}&lon=${currentPoint.lon}&radius_m=${radius}${getCategoryQuery()}`;
  const places = await apiGet(query);
  drawPlaces(places);
  renderTable(places);

  radiusCircle = L.circle([currentPoint.lat, currentPoint.lon], {
    radius,
    color: "#0d6f63",
    fillColor: "#0d6f63",
    fillOpacity: 0.12
  }).addTo(map);
}

async function demoPolygonSearch() {
  // Run a demo polygon search with a fixed rectangle.
  const payload = {
    coordinates: [
      [18.2390, 49.8360],
      [18.2860, 49.8360],
      [18.2860, 49.8070],
      [18.2390, 49.8070]
    ],
    category: categorySelect.value || null
  };

  const places = await apiPost("/places/in-polygon", payload);
  clearResultsLayers();
  const polygon = L.polygon(
    payload.coordinates.map(([lon, lat]) => [lat, lon]),
    { color: "#bc6c25", fillOpacity: 0.12 }
  ).addTo(markersLayer);

  for (const place of places) {
    L.marker([place.latitude, place.longitude])
      .bindPopup(`<strong>${place.name}</strong><br>${place.category}`)
      .addTo(markersLayer);
  }

  renderTable(places);
  map.fitBounds(polygon.getBounds(), { padding: [20, 20] });
}

function clearMap() {
  // Clear results from map and table.
  clearResultsLayers();
  renderTable([]);
}

async function checkBackend() {
  // Ping the backend and update the status label.
  try {
    const data = await apiGet("/health");
    backendStatus.textContent = data.status;
  } catch (error) {
    backendStatus.textContent = "offline";
    console.error(error);
  }
}

map.on("click", (event) => {
  // Update selected point on map click.
  setSelectedPoint(event.latlng.lat, event.latlng.lng);
});

// Load all places on button click.
document.getElementById("load-all-btn").addEventListener("click", async () => {
  try {
    await loadAllPlaces();
  } catch (error) {
    alert(error.message);
  }
});

// Run nearest search on button click.
document.getElementById("nearest-btn").addEventListener("click", async () => {
  try {
    await findNearestPlaces();
  } catch (error) {
    alert(error.message);
  }
});

// Run radius search on button click.
document.getElementById("radius-btn").addEventListener("click", async () => {
  try {
    await findWithinRadius();
  } catch (error) {
    alert(error.message);
  }
});

// Run polygon demo search on button click.
document.getElementById("polygon-btn").addEventListener("click", async () => {
  try {
    await demoPolygonSearch();
  } catch (error) {
    alert(error.message);
  }
});

// Clear map and results on button click.
document.getElementById("clear-btn").addEventListener("click", () => {
  clearMap();
});

// Initialize empty table and load initial data.
renderTable([]);
checkBackend();
loadCategories().catch((error) => console.error(error));
