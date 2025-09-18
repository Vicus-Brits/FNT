// GLOBAL
let currentSessionId = null;
let currentPage = "home";
let spotifyConnected = false; // Track Spotify connection status

// HELPERS
function showSpinner(container, message) {
  container.innerHTML = `
    <div class="text-center py-3">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="mt-2">${message}</p>
    </div>
  `;
}

function showError(container, message) {
  container.innerHTML = `<div class="alert alert-danger">${message}</div>`;
}

// Get CSRF token from cookies
function getCSRFToken() {
  const cookies = document.cookie.split(";");
  for (let cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === "csrftoken") {
      return value;
    }
  }
  return "";
}

// SESSION MANAGEMENT
// Update html
function displaySessionId(sessionId) {
  const sessionIdDiv = document.getElementById("sessionId");
  const sessionDisplay = document.getElementById("sessionDisplay");
  sessionIdDiv.innerHTML = `<strong>${sessionId}</strong>`;
  sessionIdDiv.className = "alert alert-success";
  sessionDisplay.style.display = "block";

  const newSessionBtn = document.getElementById("newSessionBtn");
  const clearSessionBtn = document.getElementById("clearSessionBtn");
  newSessionBtn.style.display = "none";
  clearSessionBtn.style.display = "inline-block";
}
// create session
async function createNewSession() {
  const button = document.getElementById("newSessionBtn");
  const statusDiv = document.getElementById("statusMessage");

  button.disabled = true;
  button.innerHTML = "Creating Session...";
  statusDiv.innerHTML =
    '<div class="spinner-border spinner-border-sm text-primary" role="status"></div> Creating new session...';

  const response = await fetch("/api/sessions/start_session/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
  });
  console.log(response);

  const data = await response.json();
  currentSessionId = data.session.session_id; // set global var
  localStorage.setItem("fnt_session_id", currentSessionId); // set localStorage
  displaySessionId(currentSessionId); // udate html

  statusDiv.innerHTML = "";
  button.disabled = false;
  button.innerHTML = "New Session";

  navigate("search-section");
}
// remove session
function clearStoredSession() {
  localStorage.removeItem("fnt_session_id");
  currentSessionId = null;
  displaySessionId(null);
  document.getElementById("statusMessage").innerHTML = "";
  // alert("Session cleared");
  // fresh page to reset state
  window.location.reload();
}

// NAVIGATION GETDATA
// refactor to a single function
async function loadPlaylist() {
  let session_id = currentSessionId;
  let container = document.getElementById("playlistContent");

  // Check if we have a session ID
  if (!session_id) {
    container.innerHTML =
      '<div class="alert alert-warning">Please create a session first</div>';
    return;
  }

  // placeholder
  container.innerHTML =
    '<div class="text-center py-3">' +
    '<div class="spinner-border text-primary" role="status"></div>' +
    '<p class="mt-2">Loading playlist...</p>' +
    "</div>";

  try {
    let response = await fetch(
      "/api/get-songs/?session_id=" + session_id + "&list_type=playlist"
    );

    if (!response.ok) {
      throw new Error("HTTP " + response.status);
    }

    let data = await response.json();
    displayPlaylist(data);
  } catch (error) {
    console.error("Error loading playlist:", error);
    container.innerHTML =
      '<div class="alert alert-danger">Failed to load playlist: ' +
      error.message +
      "</div>";
  }
}
async function loadVibe() {
  let session_id = currentSessionId;
  let container = document.getElementById("vibeContent");

  // Check if we have a session ID
  if (!session_id) {
    container.innerHTML =
      '<div class="alert alert-warning">Please create a session first</div>';
    return;
  }

  // placeholder
  container.innerHTML =
    '<div class="text-center py-3">' +
    '<div class="spinner-border text-primary" role="status"></div>' +
    '<p class="mt-2">Loading vibe...</p>' +
    "</div>";

  try {
    let response = await fetch(
      "/api/get-songs/?session_id=" + session_id + "&list_type=vibe"
    );

    if (!response.ok) {
      throw new Error("HTTP " + response.status);
    }

    let data = await response.json();
    displayVibe(data);
  } catch (error) {
    console.error("Error loading vibe:", error);
    container.innerHTML =
      '<div class="alert alert-danger">Failed to load vibe: ' +
      error.message +
      "</div>";
  }
}

// NAVIGATION
function updateNavigation(activePage) {
  // remove active from all
  document.querySelectorAll(".navbar-nav .nav-link").forEach((link) => {
    link.classList.remove("active");
  });

  // Map page names to navigation IDs
  const pageNavMap = {
    "home-section": "nav-home",
    "search-section": "nav-search",
    "playlist-section": "nav-playlist",
    "recommend-section": "nav-recommend",
    "myvibe-section": "nav-myvibe",
    "spotify-section": "nav-spotify",
  };

  // set active
  const navId = pageNavMap[activePage];
  let activeNavItem = document.querySelector(`#${navId}`);
  if (activeNavItem) {
    activeNavItem.classList.add("active");
  }

  // if mobile, close navbar,  new trick https://getbootstrap.com/docs/4.0/components/collapse/
  let navbarCollapse = document.querySelector(".navbar-collapse");
  if (navbarCollapse && navbarCollapse.classList.contains("show")) {
    const bsCollapse = new bootstrap.Collapse(navbarCollapse, {
      toggle: false,
    });
    bsCollapse.hide();
  }
}
function navigate(newPage) {
  // hide all
  document.querySelectorAll(".content-section").forEach((section) => {
    section.classList.add("d-none"); // bootstrap hide
  });

  let newSection = document.getElementById(newPage);
  newSection.classList.remove("d-none");
  currentPage = newPage;

  // get data if required
  if (newPage === "playlist-section") {
    loadPlaylist();
  }
  if (newPage === "myvibe-section") {
    loadVibe();
  }
  if (newPage === "spotify-section") {
    // Only check connection if we think user might be connected
    // This avoids 401 errors when user hasn't connected yet
    if (spotifyConnected) {
      checkSpotifyConnection();
    } else {
      // User hasn't connected yet, just ensure button shows disconnected state
      updateSpotifyButtonState("disconnected");
    }
  }

  // navbar state
  updateNavigation(newPage);

  // Update browser - refactor to hash?
  // https://stackoverflow.com/questions/9340121/what-are-the-differences-between-history-pushstate-location-hash
  if (window.location.hash !== `#${newPage}`) {
    history.pushState({ newPage }, "", `#${newPage}`);
  }
}

// SEARCH MAIN
// --NAV Buttons
function showArtistSearch() {
  document.getElementById("artist-search-component").classList.remove("d-none");
  document.getElementById("song-search-component").classList.add("d-none");
  // Clear previous results
  document.getElementById("searchResults").innerHTML = "";
  document.getElementById("songSearchResults").innerHTML = "";
}
function showSongSearch() {
  document.getElementById("song-search-component").classList.remove("d-none");
  document.getElementById("artist-search-component").classList.add("d-none");
  // Clear previous results
  document.getElementById("searchResults").innerHTML = "";
  document.getElementById("songSearchResults").innerHTML = "";
}

// --SEARCH ARTIST
async function searchArtist() {
  const input = document.getElementById("artistSearchInput");
  const resultsDiv = document.getElementById("searchResults");
  const artistName = input.value.trim();

  if (!artistName) {
    resultsDiv.innerHTML =
      '<div class="alert alert-warning">Please enter an artist name</div>';
    return;
  }
  // call Spinner Element, (replace when data is loaded)
  showSpinner(resultsDiv, `Searching for "${artistName}"...`);

  try {
    const response = await fetch(
      `/api/artist-search-lfm/?session_id=${currentSessionId}&artist_name=${encodeURIComponent(
        artistName
      )}`
    );

    if (response.ok) {
      const data = await response.json();
      displaySearchResults(data);
      console.log(data);
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  } catch (error) {
    console.error("Artist search failed:", error);
    showError(resultsDiv, `Search failed: ${error.message}`);
  }
}
// --SELECT ARTIST
async function selectArtist(artistName, artistMbid) {
  const resultsDiv = document.getElementById("searchResults");

  // Spinner
  showSpinner(resultsDiv, `Loading songs by ${artistName}...`);

  try {
    // Build API URL
    const params = new URLSearchParams({
      session_id: currentSessionId,
      artist_name: artistName,
    });

    if (artistMbid) {
      params.append("artist_mbid", artistMbid);
    }
    // call API
    const response = await fetch(`/api/artist-search-song-lfm/?${params}`);

    if (response.ok) {
      const data = await response.json();
      displayArtistSongResults(data, artistName);

      console.log(data);
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  } catch (error) {
    console.error("Artist song search failed:", error);
    showError(resultsDiv, `Failed to load songs: ${error.message}`);
  }
}
// -----Search Artist helper
function displaySearchResults(data) {
  const resultsDiv = document.getElementById("searchResults");
  const artists = data.results.artists;

  if (artists && artists.length > 0) {
    let html = '<h6>Search Results:</h6><div class="list-group">';

    artists.forEach((artist) => {
      html += `
        <div class="list-group-item">
          <div class="d-flex w-100 justify-content-between">
            <h6 class="mb-1">${artist.name}</h6>
            <button class="btn btn-spotify btn-sm" onclick="selectArtist('${artist.name.replace(
              /'/g,
              "\\'"
            )}', '${artist.mbid || ""}')">
              Select
            </button>
          </div>
        </div>
      `;
    });

    html += "</div>";
    resultsDiv.innerHTML = html; // overwrite spinner
  } else {
    resultsDiv.innerHTML =
      '<div class="alert alert-info">No artists found</div>';
  }
}
// -----Display Artist helper
function displayArtistSongResults(data, artistName) {
  const resultsDiv = document.getElementById("searchResults");
  const tracks = data.results.tracks;

  if (tracks && tracks.length > 0) {
    let html = `<h6>Songs by ${artistName}:</h6><div class="list-group">`;

    tracks.forEach((track, index) => {
      // unique ID for each result
      const songId = `artist-song-result-${index}-${Date.now()}`;
      html += `
        <div class="list-group-item" id="${songId}">
          <div class="d-flex w-100 justify-content-between">
            <div>
              <h6 class="mb-1">${track.name}</h6>
            </div>
            <button class="btn btn-spotify btn-sm" onclick="addSongToPlaylistVibe('${track.name.replace(
              /'/g,
              "\\'"
            )}', '${(track.artist || artistName).replace(/'/g, "\\'")}', '${
        track.mbid || ""
      }', '', '${songId}')">
              Add
            </button>
          </div>
        </div>
      `;
    });

    html += `</div>
      <div class="mt-3">
        <button class="btn btn-outline-secondary" onclick="goBackToArtistSearch()">
          ← Back to Artist Search
        </button>
      </div>`;
    resultsDiv.innerHTML = html;
  } else {
    resultsDiv.innerHTML = `
      <div class="alert alert-info">No songs found for ${artistName}</div>
      <div class="mt-3">
        <button class="btn btn-outline-secondary" onclick="goBackToArtistSearch()">
          ← Back to Artist Search
        </button>
      </div>`;
  }
}

async function searchSong() {
  const songInput = document.getElementById("songSearchInput");
  const artistInput = document.getElementById("songArtistInput");
  const resultsDiv = document.getElementById("songSearchResults");
  const songName = songInput.value.trim();
  const artistName = artistInput.value.trim();

  if (!songName) {
    resultsDiv.innerHTML =
      '<div class="alert alert-warning">Please enter a song name</div>';
    return;
  }
  // spimmer
  showSpinner(
    resultsDiv,
    `Searching for "${songName}"${artistName ? ` by ${artistName}` : ""}...`
  );

  try {
    const params = new URLSearchParams({
      session_id: currentSessionId,
      song_name: songName,
    });

    if (artistName) {
      params.append("artist_name", artistName);
    }
    // API Call song search
    const response = await fetch(`/api/song-search-lfm/?${params}`);

    if (response.ok) {
      const data = await response.json();
      displaySongSearchResults(data);
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  } catch (error) {
    console.error("Song search failed:", error);
    showError(resultsDiv, `Search failed: ${error.message}`);
  }
}

// ----helper displaySongSearchResults
function displaySongSearchResults(data) {
  const resultsDiv = document.getElementById("songSearchResults");
  const tracks = data.results.tracks;

  if (tracks && tracks.length > 0) {
    let html = '<h6>Search Results:</h6><div class="list-group">';

    tracks.forEach((track, index) => {
      // Generate unique ID for each result
      const songId = `song-result-${index}`;
      html += `
        <div class="list-group-item" id="${songId}">
          <div class="d-flex w-100 justify-content-between">
            <div>
              <h6 class="mb-1">${track.name}</h6>
              <p class="mb-1 text-muted">by ${track.artist}</p>
            </div>
            <button class="btn btn-spotify btn-sm" onclick="addSongToPlaylistVibe('${track.name.replace(
              /'/g,
              "\\'"
            )}', '${track.artist.replace(/'/g, "\\'")}', '${
        track.mbid || ""
      }', '', '${songId}')">
              Add
            </button>
          </div>
        </div>
      `;
    });

    html += "</div>";
    resultsDiv.innerHTML = html;
  } else {
    resultsDiv.innerHTML = '<div class="alert alert-info">No songs found</div>';
  }
}

// PLAYLIST
// PLAYLIST IS LOADed on navigation
// -- display playlist helper
function displayPlaylist(data) {
  const playlistContent = document.getElementById("playlistContent");
  const songs = data.songs;

  if (songs && songs.length > 0) {
    let html = `<h6>Your Playlist (${songs.length} songs):</h6><div class="list-group" id="playlist-sortable">`;

    songs.forEach((song, index) => {
      html += `
        <div class="list-group-item playlist-item" draggable="true" data-song-id="${
          song.id
        }" data-playlist-sequence="${song.playlist_sequence}">
          <div class="d-flex w-100 justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-2">
              <div class="drag-handle me-1" style="cursor: grab;">
                <i class="fas fa-grip-vertical text-muted"></i>
              </div>
              <span class="badge bg-secondary">#${index + 1}</span>
              <h6 class="mb-1">${song.song_title} - ${song.artist_name}</h6>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-remove btn-sm" onclick="removeSongFromPlaylist('${
                song.id
              }', this)" title="Remove from playlist">
                Remove
              </button>
            </div>
          </div>
        </div>
      `;
    });

    html += "</div>";
    playlistContent.innerHTML = html;

    // Initialize drag and drop
    setupPlaylistDrag();
  } else {
    playlistContent.innerHTML = `
      <div class="alert alert-info text-center">
        <h6>Your playlist is empty</h6>
        <p class="mb-0">Add songs from the Search page to build your playlist!</p>
      </div>`;
  }
}

// -- display vibe helper
function displayVibe(data) {
  const vibeContent = document.getElementById("vibeContent");
  const songs = data?.songs || [];

  if (songs && songs.length > 0) {
    let html = `<h6>Your Vibe (${songs.length} songs):</h6><div class="list-group" id="vibe-sortable">`;

    songs.forEach((song, index) => {
      html += `
        <div class="list-group-item vibe-item" draggable="true" data-song-id="${
          song.id
        }" data-vibe-sequence="${song.vibe_sequence}">
          <div class="d-flex w-100 justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-2">
              <div class="drag-handle me-1" style="cursor: grab;">
                <i class="fas fa-grip-vertical text-muted"></i>
              </div>
              <span class="badge bg-secondary">#${index + 1}</span>
              <h6 class="mb-1">${song.song_title} - ${song.artist_name}</h6>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-remove btn-sm" onclick="removeSongFromVibe('${
                song.id
              }', this)" title="Remove from vibe">
                Remove
              </button>
            </div>
          </div>
        </div>
      `;
    });

    html += "</div>";
    vibeContent.innerHTML = html;

    // Initialize drag and drop for vibe
    setupVibeDrag();
  } else {
    vibeContent.innerHTML = `
      <div class="alert alert-info text-center">
        <h6>Your vibe is empty</h6>
        <p class="mb-0">Add songs from the Search page to build your vibe!</p>
      </div>`;
  }
}
// -- removeSongFromPlaylist helper
async function removeSongFromPlaylist(songId, buttonElement) {
  const params = new URLSearchParams({
    session_id: currentSessionId,
    id: songId,
    list_type: "playlist",
  });

  const response = await fetch(`/api/remove-list/?${params}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
  });
  console.log(response);

  // Remove the song item
  const songElement = buttonElement.closest(".list-group-item");
  if (songElement) {
    songElement.style.opacity = "0";
    setTimeout(() => {
      songElement.remove();
      // Reload playlist to update numbering
      loadPlaylist();
    }, 300);
  }
}

// -- drag and drop helper   setupPlaylistDrag
function setupPlaylistDrag() {
  const sortableContainer = document.getElementById("playlist-sortable");
  if (!sortableContainer) return;

  let draggedElement = null;
  let draggedIndex = null;

  // Add event listeners to all playlist items
  const playlistItems = sortableContainer.querySelectorAll(".playlist-item");

  playlistItems.forEach((item, index) => {
    // Drag start
    item.addEventListener("dragstart", function (e) {
      draggedElement = this;
      draggedIndex = index;
      this.classList.add("dragging");

      // Set drag effect
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/html", this.outerHTML);
    });

    // Drag end
    item.addEventListener("dragend", function (e) {
      this.classList.remove("dragging");

      // Remove drag-over class from all items
      sortableContainer.querySelectorAll(".playlist-item").forEach((item) => {
        item.classList.remove("drag-over");
      });

      draggedElement = null;
      draggedIndex = null;
    });

    // Drag over
    item.addEventListener("dragover", function (e) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";

      // Add visual indicator
      if (draggedElement && draggedElement !== this) {
        this.classList.add("drag-over");
      }
    });

    // Drag enter
    item.addEventListener("dragenter", function (e) {
      e.preventDefault();
    });

    // Drag leave
    item.addEventListener("dragleave", function (e) {
      this.classList.remove("drag-over");
    });

    // Drop
    item.addEventListener("drop", function (e) {
      e.preventDefault();
      this.classList.remove("drag-over");

      if (draggedElement && draggedElement !== this) {
        const dropIndex = Array.from(sortableContainer.children).indexOf(this);
        playlistReorder(draggedIndex, dropIndex);
      }
    });
  });
}

// --playlist reorder helper
async function playlistReorder(fromIndex, toIndex) {
  const sortableContainer = document.getElementById("playlist-sortable");
  const items = Array.from(sortableContainer.children);

  // Create new order array
  const reorderData = [];

  // Move the dragged item to new position
  const movedItem = items.splice(fromIndex, 1)[0];
  items.splice(toIndex, 0, movedItem);

  // Update the playlist_sequence for all items
  items.forEach((item, newIndex) => {
    const songId = parseInt(item.dataset.songId);
    const newSequence = newIndex + 1;

    reorderData.push({
      id: songId,
      playlist_sequence: newSequence,
    });
  });

  // Call API to update order
  const response = await fetch(
    `/api/order-playlist/?session_id=${currentSessionId}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify(reorderData),
    }
  );

  const result = await response.json();
  console.log("Playlist reordered successfully:", result);

  // Reload playlist
  await loadPlaylist();
}

// --add songs helper
async function addSongToPlaylistVibe(
  songName,
  artistName,
  songMbid,
  artistMbid,
  songElementId
) {
  const params = new URLSearchParams({
    session_id: currentSessionId,
    artist_name: artistName,
    song_name: songName,
  });
  // build request
  if (artistMbid) params.append("artist_mbid", artistMbid);
  if (songMbid) params.append("song_mbid", songMbid);
  // call API add to playlist and vibe
  const response = await fetch(`/api/add-playlist-vibe/?${params}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
  });
  console.log(response);
  // Remove the item from results
  const songElement = document.getElementById(songElementId);
  songElement.style.opacity = "0";
  setTimeout(() => songElement.remove(), 300);

  // console.log(songName, artistName, songMbid, artistMbid, songElementId);
}

// -- removeSongFromVibe helper
async function removeSongFromVibe(songId, buttonElement) {
  const params = new URLSearchParams({
    session_id: currentSessionId,
    id: songId,
    list_type: "vibe",
  });

  const response = await fetch(`/api/remove-list/?${params}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
  });
  console.log(response);

  // Remove the song item
  const songElement = buttonElement.closest(".list-group-item");
  if (songElement) {
    songElement.style.opacity = "0";
    setTimeout(() => {
      songElement.remove();
      // Reload vibe to update numbering
      loadVibe();
    }, 300);
  }
}

// -- drag and drop helper for vibe
function setupVibeDrag() {
  const sortableContainer = document.getElementById("vibe-sortable");
  if (!sortableContainer) return;

  let draggedElement = null;
  let draggedIndex = null;

  // Add event listeners to all vibe items
  const vibeItems = sortableContainer.querySelectorAll(".vibe-item");

  vibeItems.forEach((item, index) => {
    // Drag start
    item.addEventListener("dragstart", function (e) {
      draggedElement = this;
      draggedIndex = index;
      this.classList.add("dragging");

      // Set drag effect
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/html", this.outerHTML);
    });

    // Drag end
    item.addEventListener("dragend", function (e) {
      this.classList.remove("dragging");

      // Remove drag-over class from all items
      sortableContainer.querySelectorAll(".vibe-item").forEach((item) => {
        item.classList.remove("drag-over");
      });

      draggedElement = null;
      draggedIndex = null;
    });

    // Drag over
    item.addEventListener("dragover", function (e) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";

      // Add visual indicator
      if (draggedElement && draggedElement !== this) {
        this.classList.add("drag-over");
      }
    });

    // Drag enter
    item.addEventListener("dragenter", function (e) {
      e.preventDefault();
    });

    // Drag leave
    item.addEventListener("dragleave", function (e) {
      this.classList.remove("drag-over");
    });

    // Drop
    item.addEventListener("drop", function (e) {
      e.preventDefault();
      this.classList.remove("drag-over");

      if (draggedElement && draggedElement !== this) {
        const dropIndex = Array.from(sortableContainer.children).indexOf(this);
        vibeReorder(draggedIndex, dropIndex);
      }
    });
  });
}

// --vibe reorder helper
async function vibeReorder(fromIndex, toIndex) {
  const sortableContainer = document.getElementById("vibe-sortable");
  const items = Array.from(sortableContainer.children);

  // Create new order array
  const reorderData = [];

  // Move the dragged item to new position
  const movedItem = items.splice(fromIndex, 1)[0];
  items.splice(toIndex, 0, movedItem);

  // Update the vibe_sequence for all items
  items.forEach((item, newIndex) => {
    const songId = parseInt(item.dataset.songId);
    const newSequence = newIndex + 1;

    reorderData.push({
      id: songId,
      vibe_sequence: newSequence,
    });
  });

  // Call API to update order
  const response = await fetch(
    `/api/order-vibe/?session_id=${currentSessionId}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify(reorderData),
    }
  );

  const result = await response.json();
  console.log("Vibe reordered successfully:", result);

  // Reload vibe
  await loadVibe();
}

// Helper functions for navigation
function goBackToArtistSearch() {
  document.getElementById("searchResults").innerHTML = "";
  document.getElementById("artistSearchInput").value = "";
}

// Initialize app on page load
document.addEventListener("DOMContentLoaded", function () {
  // Check if there's a stored session
  const storedSessionId = localStorage.getItem("fnt_session_id");
  if (storedSessionId) {
    currentSessionId = storedSessionId;
    displaySessionId(storedSessionId);
  }

  // Check for Spotify callback parameters first
  checkSpotifyCallback();

  // Only check Spotify connection if we're navigating to the Spotify section
  // or if there was a successful callback
  // Don't check on every page load to avoid unnecessary 401 errors

  // Handle hash navigation
  const hash = window.location.hash;
  if (hash) {
    const page = hash.substring(1);
    if (document.getElementById(page)) {
      navigate(page);
    }
  }
});

// Recommendation functions placeholders
function showArtistRecommend() {
  document
    .getElementById("artist-recommend-component")
    .classList.remove("d-none");
  document.getElementById("vibe-recommend-component").classList.add("d-none");
  // Clear previous results
  document.getElementById("recommendationsResults").innerHTML = "";
  document.getElementById("vibeRecommendationsResults").innerHTML = "";
}

function showVibeRecommend() {
  document
    .getElementById("vibe-recommend-component")
    .classList.remove("d-none");
  document.getElementById("artist-recommend-component").classList.add("d-none");
  // Clear previous results
  document.getElementById("recommendationsResults").innerHTML = "";
  document.getElementById("vibeRecommendationsResults").innerHTML = "";
}

async function getRecommendations() {
  const input = document.getElementById("recommendArtistInput");
  const resultsDiv = document.getElementById("recommendationsResults");
  const artistName = input.value.trim();

  if (!artistName) {
    resultsDiv.innerHTML =
      '<div class="alert alert-warning">Please enter an artist name</div>';
    return;
  }

  showSpinner(resultsDiv, `Getting recommendations for "${artistName}"...`);

  try {
    const response = await fetch(
      `/api/recommend/?session_id=${currentSessionId}&artist_name=${encodeURIComponent(
        artistName
      )}`
    );

    if (response.ok) {
      const data = await response.json();
      showResults(data, artistName);
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  } catch (error) {
    console.error("Recommendations failed:", error);
    showError(resultsDiv, `Failed to get recommendations: ${error.message}`);
  }
}

async function getVibeRecommendations() {
  const resultsDiv = document.getElementById("vibeRecommendationsResults");

  if (!currentSessionId) {
    resultsDiv.innerHTML =
      '<div class="alert alert-warning">Please create a session first</div>';
    return;
  }

  showSpinner(resultsDiv, "Getting vibe-based recommendations...");

  try {
    // For now, this is a placeholder - you might need to implement a specific vibe-based recommendation endpoint
    resultsDiv.innerHTML = '<div class="alert alert-info">TODO</div>';
  } catch (error) {
    console.error("Vibe recommendations failed:", error);
    showError(
      resultsDiv,
      `Failed to get vibe recommendations: ${error.message}`
    );
  }
}

function showResults(data, artistName) {
  const resultsDiv = document.getElementById("recommendationsResults");
  const recommendations = data.results?.recommendations || [];

  if (recommendations && recommendations.length > 0) {
    let html = `<h6>Recommendations based on ${artistName}:</h6><div class="list-group">`;

    recommendations.forEach((track, index) => {
      const songId = `rec-song-result-${index}-${Date.now()}`;
      html += `
        <div class="list-group-item" id="${songId}">
          <div class="d-flex w-100 justify-content-between">
            <div>
              <h6 class="mb-1">${track.name}</h6>
              <p class="mb-1 text-muted">by ${track.artist_name}</p>
            </div>
            <button class="btn btn-spotify btn-sm" onclick="addSongToPlaylistVibe('${track.name.replace(
              /'/g,
              "\\'"
            )}', '${track.artist_name.replace(/'/g, "\\'")}', '${
        track.mbid || ""
      }', '${track.artist_mbid || ""}', '${songId}')">
              Add
            </button>
          </div>
        </div>
      `;
    });

    html += "</div>";
    resultsDiv.innerHTML = html;
  } else {
    resultsDiv.innerHTML = `<div class="alert alert-info">No recommendations found for ${artistName}</div>`;
  }
}

// PLAY NEXT FROM FNT FUNCTIONALITY

// Get the first song from user's playlist
async function getFirstPlaylistSong() {
  if (!currentSessionId) {
    throw new Error("No active session. Please create a session first.");
  }

  try {
    const response = await fetch(
      `/api/get-songs/?session_id=${currentSessionId}&list_type=playlist`
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    const songs = data.songs;

    if (!songs || songs.length === 0) {
      throw new Error(
        "Your playlist is empty. Add some songs to your playlist first."
      );
    }

    // Find the song with playlist_sequence = 1 (or the first song if no explicit sequence)
    const firstSong =
      songs.find((song) => song.playlist_sequence === 1) || songs[0];

    return {
      title: firstSong.song_title,
      artist: firstSong.artist_name,
      id: firstSong.id,
    };
  } catch (error) {
    console.error("Error getting first playlist song:", error);
    throw error;
  }
}

// Main function to play next song from FNT playlist
async function playNextFromFNT() {
  const button = document.getElementById("playNextFromFNTBtn");
  const originalHTML = button.innerHTML;

  // Show loading state
  button.disabled = true;
  button.innerHTML =
    '<i class="fas fa-spinner fa-spin me-1"></i>Finding song...';

  try {
    // Step 1: Get the first song from playlist
    const firstSong = await getFirstPlaylistSong();

    button.innerHTML =
      '<i class="fas fa-spinner fa-spin me-1"></i>Searching Spotify...';

    // Step 2: Search for the song on Spotify
    const spotifyTrack = await searchSpotifyForSong(
      firstSong.title,
      firstSong.artist
    );

    button.innerHTML =
      '<i class="fas fa-spinner fa-spin me-1"></i>Playing song...';

    // Step 3: Play the song on Spotify
    await playSpotifyTrack(spotifyTrack.uri);

    // Step 4: Show success message and update currently playing
    const statusDiv = document.getElementById("spotifyStatus");
    if (statusDiv) {
      const successMessage = document.createElement("div");
      successMessage.className = "alert alert-success mt-2";
      successMessage.innerHTML = `
        <h6><i class="fas fa-check-circle me-2"></i>Now Playing from FNT!</h6>
        <p class="mb-0">
          <strong>${spotifyTrack.name}</strong> by ${spotifyTrack.artists}
        </p>
      `;

      // Remove any existing success messages
      const existingMessages = statusDiv.querySelectorAll(".alert-success");
      existingMessages.forEach((msg) => {
        if (msg.innerHTML.includes("Now Playing from FNT!")) {
          msg.remove();
        }
      });

      statusDiv.appendChild(successMessage);

      // Remove the message after 5 seconds
      setTimeout(() => {
        successMessage.remove();
      }, 5000);
    }

    // Refresh currently playing info after a brief delay
    setTimeout(() => {
      refreshCurrentlyPlaying();
    }, 2000);
  } catch (error) {
    console.error("Error playing next from FNT:", error);

    // Show error message
    const statusDiv = document.getElementById("spotifyStatus");
    if (statusDiv) {
      const errorMessage = document.createElement("div");
      errorMessage.className = "alert alert-danger mt-2";
      errorMessage.innerHTML = `
        <h6><i class="fas fa-exclamation-circle me-2"></i>Could not play from FNT</h6>
        <p class="mb-0">${error.message}</p>
      `;

      // Remove any existing error messages
      const existingMessages = statusDiv.querySelectorAll(".alert-danger");
      existingMessages.forEach((msg) => {
        if (msg.innerHTML.includes("Could not play from FNT")) {
          msg.remove();
        }
      });

      statusDiv.appendChild(errorMessage);

      // Remove the error message after 8 seconds
      setTimeout(() => {
        errorMessage.remove();
      }, 8000);
    }
  } finally {
    // Restore button state
    button.disabled = false;
    button.innerHTML = originalHTML;
  }
}
