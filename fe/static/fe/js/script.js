// GLOBAL
let currentSessionId = null;
let currentPage = "home";
let spotifyConnected = false;

// HELPERS
function showSpinner(container, message) {
  container.innerHTML = `
    <div class="text-center py-3">
      <div class="spinner-border" role="status"></div>
      <p class="mt-2">${message}</p>
    </div>
  `;
}

function getCSRFToken() {
  const cookies = document.cookie.split(";");
  for (let cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === "csrftoken") return value;
  }
  return "";
}

// SESSION MANAGEMENT
const SessionStates = {
  NO_SESSION: "no-session",
  CREATING: "creating",
  ACTIVE: "active",
};
let sessionState = SessionStates.NO_SESSION;

function updateSessionUI(state, sessionId = null) {
  const sessionCreate = document.getElementById("sessionCreate");
  const sessionActive = document.getElementById("sessionActive");
  const newSessionBtn = document.getElementById("newSessionBtn");
  const sessionBtnText = document.getElementById("sessionBtnText");
  const sessionIdDisplay = document.getElementById("sessionId");

  newSessionBtn.classList.remove("btn-loading");

  if (state === SessionStates.NO_SESSION) {
    sessionCreate.style.display = "block";
    sessionActive.style.display = "none";
    sessionBtnText.textContent = "New Session";
    newSessionBtn.disabled = false;
    updateNavigationAccess(false);
  } else if (state === SessionStates.CREATING) {
    sessionCreate.style.display = "block";
    sessionActive.style.display = "none";
    newSessionBtn.classList.add("btn-loading");
    sessionBtnText.textContent = "Creating...";
    newSessionBtn.disabled = true;
  } else if (state === SessionStates.ACTIVE) {
    sessionCreate.classList.add("session-fade-out");
    setTimeout(() => {
      sessionCreate.style.display = "none";
      sessionCreate.classList.remove("session-fade-out");
      sessionIdDisplay.textContent = sessionId;
      sessionActive.style.display = "block";
      sessionActive.classList.add("session-fade-in");
      updateNavigationAccess(true);
    }, 300);
  }

  sessionState = state;
}

// if there is no session id, disable nav links (not best plan)
function updateNavigationAccess(hasSession) {
  const navLinks = document.querySelectorAll(
    ".navbar-nav .nav-link:not(#nav-home)"
  );
  const sessionRequiredDiv = document.getElementById("sessionRequired");
  navLinks.forEach((link) =>
    hasSession
      ? link.classList.remove("disabled")
      : link.classList.add("disabled")
  );
  if (sessionRequiredDiv)
    sessionRequiredDiv.style.display = hasSession ? "none" : "block";
}

async function createNewSession() {
  updateSessionUI(SessionStates.CREATING); // wait state
  const response = await fetch("/api/sessions/start/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
  });

  if (!response.ok) {
    return updateSessionUI(SessionStates.NO_SESSION);
  }

  const data = await response.json();
  currentSessionId = data.session.session_id;
  // TODO check if local storage still needed
  localStorage.setItem(
    "fnt_session_data",
    JSON.stringify({ id: currentSessionId, created: Date.now() })
  );
  updateSessionUI(SessionStates.ACTIVE, currentSessionId);

  // Modal Pop Up  to guide user
  const modal = new bootstrap.Modal(
    document.getElementById("sessionCreatedModal")
  );
  modal.show();
}

// Helper: clear session data nav to home
function clearLocal() {
  localStorage.removeItem("fnt_session_data");
  localStorage.removeItem("fnt_session_id");
  currentSessionId = null;
  updateSessionUI(SessionStates.NO_SESSION);
  navigate("home-section");
}

// Clear stored session (local + server)
async function clearStoredSession(id = currentSessionId) {
  const statusDiv = document.getElementById("statusMessage");
  // clear database
  await fetch(
    `/api/clear-session-songs/?session_id=${encodeURIComponent(id)}`,
    {
      method: "POST",
    }
  );
  // delete session
  await fetch(`/api/sessions/${encodeURIComponent(id)}/stop/`, {
    method: "DELETE",
  });
  // clear localStorage
  clearLocal();
}

async function restoreSession() {
  const sessionDataStr = localStorage.getItem("fnt_session_data");
  let sessionId = sessionDataStr
    ? JSON.parse(sessionDataStr).id
    : localStorage.getItem("fnt_session_id");
  if (!sessionId) {
    updateSessionUI(SessionStates.NO_SESSION);
    return false;
  }

  const response = await fetch(`/api/sessions/${sessionId}/check/`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
  });

  if (!response.ok) {
    clearLocalSession();
    updateSessionUI(SessionStates.NO_SESSION);
    return false;
  }
  const data = await response.json();
  if (!data.session.is_active) {
    clearLocalSession();
    updateSessionUI(SessionStates.NO_SESSION);
    return false;
  }

  currentSessionId = sessionId;
  if (!sessionDataStr) {
    localStorage.setItem(
      "fnt_session_data",
      JSON.stringify({ id: sessionId, created: Date.now() })
    );
    localStorage.removeItem("fnt_session_id");
  }
  updateSessionUI(SessionStates.ACTIVE, currentSessionId);
  return true;
}

function clearLocalSession() {
  localStorage.removeItem("fnt_session_data");
  localStorage.removeItem("fnt_session_id");
  currentSessionId = null;
}

function displaySessionId(sessionId) {
  updateSessionUI(
    sessionId ? SessionStates.ACTIVE : SessionStates.NO_SESSION,
    sessionId || undefined
  );
}

// DATA LOADERS
async function loadPlaylist() {
  const container = document.getElementById("playlistContent");
  if (!currentSessionId) {
    container.innerHTML =
      '<div class="alert alert-warning">Please create a session first to view your playlist</div>';
    return;
  }
  showSpinner(container, "Loading playlist...");
  const response = await fetch(
    `/api/get-songs/?session_id=${currentSessionId}&list_type=playlist`
  );
  const data = await response.json();
  displayPlaylist(data);
}

async function loadVibe() {
  const container = document.getElementById("vibeContent");
  if (!currentSessionId) {
    container.innerHTML =
      '<div class="alert alert-warning">Please create a session first to view your vibe</div>';
    return;
  }
  showSpinner(container, "Loading vibe...");
  const response = await fetch(
    `/api/get-songs/?session_id=${currentSessionId}&list_type=vibe`
  );
  const data = await response.json();
  displayVibe(data);
}

// NAVIGATION
function updateNavigation(activePage) {
  document
    .querySelectorAll(".navbar-nav .nav-link")
    .forEach((link) => link.classList.remove("active"));
  const pageNavMap = {
    "home-section": "nav-home",
    "search-section": "nav-search",
    "playlist-section": "nav-playlist",
    "recommend-section": "nav-recommend",
    "myvibe-section": "nav-myvibe",
    "spotify-section": "nav-spotify",
  };
  const navId = pageNavMap[activePage];
  const activeNavItem = document.getElementById(navId);
  if (activeNavItem) activeNavItem.classList.add("active");

  const navbarCollapse = document.querySelector(".navbar-collapse");
  if (navbarCollapse && navbarCollapse.classList.contains("show"))
    new bootstrap.Collapse(navbarCollapse, { toggle: false }).hide();
}

function navigate(newPage) {
  document
    .querySelectorAll(".content-section")
    .forEach((s) => s.classList.add("d-none"));
  const newSection = document.getElementById(newPage);
  if (!newSection) return;
  newSection.classList.remove("d-none");
  currentPage = newPage;

  if (newPage === "playlist-section") loadPlaylist();
  if (newPage === "myvibe-section") loadVibe();
  if (newPage === "spotify-section") checkSpotifyConnection?.();

  updateNavigation(newPage);
  if (window.location.hash !== `#${newPage}`)
    history.pushState({ newPage }, "", `#${newPage}`);
}

// SEARCH MAIN
function showArtistSearch() {
  document.getElementById("artist-search-component").classList.remove("d-none");
  document.getElementById("song-search-component").classList.add("d-none");
  document.getElementById("searchResults").innerHTML = "";
  document.getElementById("songSearchResults").innerHTML = "";
  // make songSearchBtn less prominent (consider helper function)
  document.getElementById("songSearchBtn").className =
    "btn btn-outline-spotify btn-lg w-100 py-3";
  document.getElementById("artistSearchBtn").className =
    "btn btn-spotify btn-lg w-100 py-3";
}

function showSongSearch() {
  document.getElementById("song-search-component").classList.remove("d-none");
  document.getElementById("artist-search-component").classList.add("d-none");
  document.getElementById("searchResults").innerHTML = "";
  document.getElementById("songSearchResults").innerHTML = "";
  // make artistSearchBtn less prominent
  document.getElementById("artistSearchBtn").className =
    "btn btn-outline-spotify btn-lg w-100 py-3";
  document.getElementById("songSearchBtn").className =
    "btn btn-spotify btn-lg w-100 py-3";
}

async function searchArtist() {
  const input = document.getElementById("artistSearchInput");
  const resultsDiv = document.getElementById("searchResults");
  const artistName = input.value.trim();
  if (!artistName) {
    resultsDiv.innerHTML =
      '<div class="alert alert-warning">Please enter an artist name</div>';
    return;
  }
  showSpinner(resultsDiv, `Searching for "${artistName}"...`);
  const response = await fetch(
    `/api/artist-search-lfm/?session_id=${currentSessionId}&artist_name=${encodeURIComponent(
      artistName
    )}`
  );
  const data = await response.json();
  displaySearchResults(data);
}

async function selectArtist(artistName, artistMbid) {
  const resultsDiv = document.getElementById("searchResults");
  showSpinner(resultsDiv, `Loading songs by ${artistName}...`);
  const params = new URLSearchParams({
    session_id: currentSessionId,
    artist_name: artistName,
  });
  if (artistMbid) params.append("artist_mbid", artistMbid);
  const response = await fetch(`/api/artist-search-song-lfm/?${params}`);
  const data = await response.json();
  displayArtistSongResults(data, artistName);
}

function displaySearchResults(data) {
  const resultsDiv = document.getElementById("searchResults");
  const artists = data.results.artists;
  if (artists?.length) {
    let html = '<h6>Search Results:</h6><div class="list-group">';
    artists.forEach((artist) => {
      html += `
        <div class="list-group-item">
          <div class="d-flex w-100 justify-content-between">
            <h6 class="mb-1">${artist.name}</h6>
            <button class="btn btn-spotify btn-sm" onclick="selectArtist('${artist.name.replace(
              /'/g,
              "\\'"
            )}', '${artist.mbid || ""}')">Select</button>
          </div>
        </div>`;
    });
    resultsDiv.innerHTML = html + "</div>";
  } else {
    resultsDiv.innerHTML =
      '<div class="alert alert-info">No artists found</div>';
  }
}

function displayArtistSongResults(data, artistName) {
  const resultsDiv = document.getElementById("searchResults");
  const tracks = data.results.tracks;
  if (tracks?.length) {
    let html = `<h6>Songs by ${artistName}:</h6><div class="list-group">`;
    tracks.forEach((track, index) => {
      const songId = `artist-song-result-${index}-${Date.now()}`;
      html += `
        <div class="list-group-item" id="${songId}">
          <div class="d-flex w-100 justify-content-between">
            <div><h6 class="mb-1">${track.name}</h6></div>
            <button class="btn btn-spotify btn-sm" onclick="addSongToPlaylistVibe('${track.name.replace(
              /'/g,
              "\\'"
            )}', '${(track.artist || artistName).replace(/'/g, "\\'")}', '${
        track.mbid || ""
      }', '', '${songId}')">Add</button>
          </div>
        </div>`;
    });
    resultsDiv.innerHTML =
      html +
      `</div><div class="mt-3"><button class="btn btn-outline-secondary" onclick="goBackToArtistSearch()">← Back to Artist Search</button></div>`;
  } else {
    resultsDiv.innerHTML = `<div class="alert alert-info">No songs found for ${artistName}</div><div class="mt-3"><button class="btn btn-outline-secondary" onclick="goBackToArtistSearch()">← Back to Artist Search</button></div>`;
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
  showSpinner(
    resultsDiv,
    `Searching for "${songName}"${artistName ? ` by ${artistName}` : ""}...`
  );
  const params = new URLSearchParams({
    session_id: currentSessionId,
    song_name: songName,
  });
  if (artistName) params.append("artist_name", artistName);
  const response = await fetch(`/api/song-search-lfm/?${params}`);
  const data = await response.json();
  displaySongSearchResults(data);
}

function displaySongSearchResults(data) {
  const resultsDiv = document.getElementById("songSearchResults");
  const tracks = data.results.tracks;
  if (tracks?.length) {
    let html = '<h6>Search Results:</h6><div class="list-group">';
    tracks.forEach((track, index) => {
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
      }', '', '${songId}')">Add</button>
          </div>
        </div>`;
    });
    resultsDiv.innerHTML = html + "</div>";
  } else {
    resultsDiv.innerHTML = '<div class="alert alert-info">No songs found</div>';
  }
}

// PLAYLIST & VIBE DISPLAY
function displayPlaylist(data) {
  const playlistContent = document.getElementById("playlistContent");
  const songs = data.songs;
  if (songs?.length) {
    let html = `<h6>Your Playlist (${songs.length} songs):</h6><div class="list-group" id="playlist-sortable">`;
    songs.forEach((song, index) => {
      html += `
        <div class="list-group-item playlist-item" draggable="true" data-song-id="${
          song.id
        }" data-playlist-sequence="${song.playlist_sequence}">
          <div class="d-flex w-100 justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-2">
              <span class="drag-handle me-1" aria-hidden="true" style="cursor: grab;">⋮⋮</span>
              <span class="badge bg-secondary">#${index + 1}</span>
              <h6 class="mb-1">${song.song_title} - ${song.artist_name}</h6>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-remove btn-sm" onclick="removeSongFromList('${
                song.id
              }', 'playlist', this)" title="Remove from playlist">Remove</button>
            </div>
          </div>
        </div>`;
    });
    playlistContent.innerHTML = html + "</div>";
    setupPlaylistDrag();
  } else {
    playlistContent.innerHTML = `<div class="alert alert-info text-center"><h6>Your playlist is empty</h6></div>`;
    playlistContent.innerHTML += `<div class="mt-3 text-center">
    <button class="btn btn-spotify" onclick="navigate('search-section')">
    <i class="bi bi-search"></i> Search for Songs
    </button>
  </div>`;
  }
}

function displayVibe(data) {
  const vibeContent = document.getElementById("vibeContent");
  const songs = data?.songs || [];
  if (songs.length) {
    let html = `<h6>Your Vibe (${songs.length} songs):</h6><div class="list-group" id="vibe-sortable">`;
    songs.forEach((song, index) => {
      html += `
        <div class="list-group-item vibe-item" draggable="true" data-song-id="${
          song.id
        }" data-vibe-sequence="${song.vibe_sequence}">
          <div class="d-flex w-100 justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-2">
              <span class="drag-handle me-1" aria-hidden="true" style="cursor: grab;">⋮⋮</span>
              <span class="badge bg-secondary">#${index + 1}</span>
              <h6 class="mb-1">${song.song_title} - ${song.artist_name}</h6>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-remove btn-sm" onclick="removeSongFromList('${
                song.id
              }', 'vibe', this)" title="Remove from vibe">Remove</button>
            </div>
          </div>
        </div>`;
    });
    vibeContent.innerHTML = html + "</div>";
    setupVibeDrag();
  } else {
    vibeContent.innerHTML = `<div class="alert alert-info text-center"><h6>Your vibe is empty</h6><p class="mb-0">Add songs from the Search page to build your vibe!</p></div>`;
  }
}

// COMMON REMOVE
async function removeSongFromList(songId, listType, btn) {
  const params = new URLSearchParams({
    session_id: currentSessionId,
    id: songId,
    list_type: listType,
  });
  await fetch(`/api/remove-list/?${params}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
  });
  const item = btn.closest(".list-group-item");
  if (item) {
    item.style.opacity = "0";
    setTimeout(() => {
      item.remove();
      if (listType === "playlist") loadPlaylist();
      else loadVibe();
    }, 200);
  }
}

// DRAG & DROP — PLAYLIST
function setupPlaylistDrag() {
  const sortable = document.getElementById("playlist-sortable");
  if (!sortable) return;
  let draggedIndex = null;
  const items = sortable.querySelectorAll(".playlist-item");
  items.forEach((item, index) => {
    item.addEventListener("dragstart", () => {
      draggedIndex = index;
      item.classList.add("dragging");
    });
    item.addEventListener("dragend", () => {
      item.classList.remove("dragging");
      sortable
        .querySelectorAll(".playlist-item")
        .forEach((i) => i.classList.remove("drag-over"));
    });
    item.addEventListener("dragover", (e) => {
      e.preventDefault();
      const currentItems = sortable.querySelectorAll(".playlist-item");
      if (draggedIndex !== null && currentItems[draggedIndex] !== item)
        item.classList.add("drag-over");
    });
    item.addEventListener("dragleave", () =>
      item.classList.remove("drag-over")
    );
    item.addEventListener("drop", async (e) => {
      e.preventDefault();
      item.classList.remove("drag-over");
      const dropIndex = Array.from(sortable.children).indexOf(item);
      await playlistReorder(draggedIndex, dropIndex);
    });
  });
}

async function playlistReorder(fromIndex, toIndex) {
  const sortable = document.getElementById("playlist-sortable");
  const items = Array.from(sortable.children);
  const moved = items.splice(fromIndex, 1)[0];
  items.splice(toIndex, 0, moved);
  const body = items.map((item, idx) => ({
    id: parseInt(item.dataset.songId),
    playlist_sequence: idx + 1,
  }));
  await fetch(`/api/order-playlist/?session_id=${currentSessionId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify(body),
  });
  await loadPlaylist();
}

// DRAG & DROP — VIBE
function setupVibeDrag() {
  const sortable = document.getElementById("vibe-sortable");
  if (!sortable) return;
  let draggedIndex = null;
  const items = sortable.querySelectorAll(".vibe-item");
  items.forEach((item, index) => {
    item.addEventListener("dragstart", () => {
      draggedIndex = index;
      item.classList.add("dragging");
    });
    item.addEventListener("dragend", () => {
      item.classList.remove("dragging");
      sortable
        .querySelectorAll(".vibe-item")
        .forEach((i) => i.classList.remove("drag-over"));
    });
    item.addEventListener("dragover", (e) => {
      e.preventDefault();
      const currentItems = sortable.querySelectorAll(".vibe-item");
      if (draggedIndex !== null && currentItems[draggedIndex] !== item)
        item.classList.add("drag-over");
    });
    item.addEventListener("dragleave", () =>
      item.classList.remove("drag-over")
    );
    item.addEventListener("drop", async (e) => {
      e.preventDefault();
      item.classList.remove("drag-over");
      const dropIndex = Array.from(sortable.children).indexOf(item);
      await vibeReorder(draggedIndex, dropIndex);
    });
  });
}

async function vibeReorder(fromIndex, toIndex) {
  const sortable = document.getElementById("vibe-sortable");
  const items = Array.from(sortable.children);
  const moved = items.splice(fromIndex, 1)[0];
  items.splice(toIndex, 0, moved);
  const body = items.map((item, idx) => ({
    id: parseInt(item.dataset.songId),
    vibe_sequence: idx + 1,
  }));
  await fetch(`/api/order-vibe/?session_id=${currentSessionId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify(body),
  });
  await loadVibe();
}

// SONG ADDITION
async function addSongToPlaylistVibe(
  songName,
  artistName,
  songMbid,
  artistMbid,
  buttonElementId
) {
  const params = new URLSearchParams({
    session_id: currentSessionId,
    song_title: songName,
    artist_name: artistName,
    list_type: "playlist,vibe",
  });
  if (songMbid) params.append("song_id", songMbid);
  if (artistMbid) params.append("artist_id", artistMbid);

  await fetch(`/api/add-song/?${params}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
  });

  document.getElementById(buttonElementId).remove();
}

// NAV HELPERS
function goBackToArtistSearch() {
  document.getElementById("searchResults").innerHTML = "";
  document.getElementById("artistSearchInput").value = "";
}

// RECOMMENDATIONS (artist-based; vibe placeholder)
function showArtistRecommend() {
  document
    .getElementById("artist-recommend-component")
    .classList.remove("d-none");
  document.getElementById("vibe-recommend-component").classList.add("d-none");
  document.getElementById("recommendationsResults").innerHTML = "";
  document.getElementById("vibeRecommendationsResults").innerHTML = "";

  // make vibeRecommendBtn less prominent (consider helper function
  document.getElementById("vibeRecommendBtn").className =
    "btn btn-outline-spotify btn-lg w-100 py-3";
  document.getElementById("artistRecommendBtn").className =
    "btn btn-spotify btn-lg w-100 py-3";
}

function showVibeRecommend() {
  document
    .getElementById("vibe-recommend-component")
    .classList.remove("d-none");
  document.getElementById("artist-recommend-component").classList.add("d-none");
  document.getElementById("recommendationsResults").innerHTML = "";
  document.getElementById("vibeRecommendationsResults").innerHTML = "";
  // make artistRecommendBtn less prominent (consider helper function
  document.getElementById("vibeRecommendBtn").className =
    "btn btn-spotify btn-lg w-100 py-3";
  document.getElementById("artistRecommendBtn").className =
    "btn btn-outline-spotify btn-lg w-100 py-3";
}

async function getRecommendations() {
  const input = document.getElementById("recommendArtistInput");
  const resultsDiv = document.getElementById("recommendationsResults");
  const artistName = input.value.trim();
  if (!currentSessionId) {
    resultsDiv.innerHTML =
      '<div class="alert alert-warning">Please create a session first to get recommendations</div>';
    return;
  }
  if (!artistName) {
    resultsDiv.innerHTML =
      '<div class="alert alert-warning">Please enter an artist name</div>';
    return;
  }
  showSpinner(resultsDiv, `Getting recommendations for "${artistName}"...`);
  const response = await fetch(
    `/api/recommend/?session_id=${currentSessionId}&artist_name=${encodeURIComponent(
      artistName
    )}`
  );
  const data = await response.json();
  showResults(data, artistName);
}

async function getVibeRecommendations() {
  const resultsDiv = document.getElementById("vibeRecommendationsResults");

  showSpinner(resultsDiv, "Getting recommendations...");

  //Get the vibe list
  const vibeResponse = await fetch(
    `/api/get-songs/?session_id=${currentSessionId}&list_type=vibe`
  );
  const vibeData = await vibeResponse.json();
  const vibeSongs = vibeData.songs || [];

  if (vibeSongs.length === 0) {
    resultsDiv.innerHTML =
      '<div class="alert alert-info">Add songs to your playlist first</div>';
    return;
  }

  // Step 2: top 5 artist from vibe (top of list)
  const uniqueArtists = [...new Set(vibeSongs.map((song) => song.artist_name))];
  const firstFiveArtists = uniqueArtists.slice(0, 5);

  // Step 3: recomendations  for each artist
  showSpinner(resultsDiv, `Getting recommendations...this can take a while..`);

  const recommendationPromises = firstFiveArtists.map((artistName) =>
    fetch(
      `/api/recommend/?session_id=${currentSessionId}&artist_name=${encodeURIComponent(
        artistName
      )}`
    )
      .then((response) => response.json())
      .catch((error) => ({ results: { recommendations: [] } }))
  );

  const allRecommendations = await Promise.all(recommendationPromises);

  // Step 4: see which songs appear most
  const trackCounts = new Map();
  const trackDetails = new Map();

  allRecommendations.forEach((recData) => {
    const recommendations = recData.results?.recommendations || [];
    recommendations.forEach((track) => {
      const trackKey = `${track.name}|${track.artist_name}`;

      if (trackCounts.has(trackKey)) {
        trackCounts.set(trackKey, trackCounts.get(trackKey) + 1);
      } else {
        trackCounts.set(trackKey, 1);
        trackDetails.set(trackKey, track);
      }
    });
  });

  // Step 5: filter out songs on the Songs table already
  const existingSongsResponse = await fetch(
    `/api/get-songs/?session_id=${currentSessionId}&list_type=playlist`
  );
  const existingSongsData = await existingSongsResponse.json();
  const existingSongs = existingSongsData.songs || [];

  // existing songs
  const existingSongKeys = new Set(
    existingSongs.map((song) => `${song.song_title}|${song.artist_name}`)
  );

  // Step 6: Filter out existing , sort by count then popularity
  const filteredTracks = Array.from(trackCounts.entries())
    .filter(([trackKey]) => !existingSongKeys.has(trackKey))
    .map(([trackKey, count]) => {
      const track = trackDetails.get(trackKey);
      return {
        ...track,
        occurrence_count: count,
      };
    })
    .sort((a, b) => {
      //sort by count
      if (b.occurrence_count !== a.occurrence_count) {
        return b.occurrence_count - a.occurrence_count;
      }
      // sort by popularity
      return (b.popularity || 0) - (a.popularity || 0);
    })
    .slice(0, 20); // Get top 20

  showVibeRecommendationsResults(filteredTracks, firstFiveArtists);
}

function showVibeRecommendationsResults(tracks, seedArtists) {
  const resultsDiv = document.getElementById("vibeRecommendationsResults");

  let html = `
    <div class="mb-3">
      <p class="text-muted mb-2">Your Current Vibe: ${seedArtists.join(
        ", "
      )}</p>
    </div>
    <div class="list-group">`;

  tracks.forEach((track, index) => {
    const songId = `vibe-rec-song-result-${index}-${Date.now()}`;

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
    }', '${track.artist_mbid || ""}', '${songId}')">Add</button>
        </div>
      </div>`;
  });

  resultsDiv.innerHTML = html + "</div>";
}

function showResults(data, artistName) {
  const resultsDiv = document.getElementById("recommendationsResults");
  const recommendations = data.results?.recommendations || [];
  if (recommendations.length) {
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
      }', '${track.artist_mbid || ""}', '${songId}')">Add</button>
          </div>
        </div>`;
    });
    resultsDiv.innerHTML = html + "</div>";
  } else {
    resultsDiv.innerHTML = `<div class="alert alert-info">No recommendations found for ${artistName}</div>`;
  }
}

// MODAL NAVIGATION
function goToSearch() {
  const modal = bootstrap.Modal.getInstance(
    document.getElementById("sessionCreatedModal")
  );
  modal.hide();
  navigate("search-section");
}

function goToRecommendations() {
  const modal = bootstrap.Modal.getInstance(
    document.getElementById("sessionCreatedModal")
  );
  if (modal) {
    modal.hide();
  }
  navigate("recommend-section");
}

function goToSpotify() {
  const modal = bootstrap.Modal.getInstance(
    document.getElementById("sessionCreatedModal")
  );
  if (modal) {
    modal.hide();
  }
  navigate("spotify-section");
}

// NAVIGATION HELPER
function goToPlaylist() {
  navigate("playlist-section");
}

function goToVibeList() {
  navigate("myvibe-section");
}

// INIT
document.addEventListener("DOMContentLoaded", async function () {
  const hasSession = await restoreSession();
  checkSpotifyCallback?.();
  const hash = window.location.hash;
  if (hash && document.getElementById(hash.substring(1)))
    navigate(hash.substring(1));
  else if (hasSession) updateNavigationAccess(true);

  window.addEventListener("storage", function (e) {
    if (e.key === "fnt_session_data") {
      if (e.newValue) {
        currentSessionId = JSON.parse(e.newValue).id;
        updateSessionUI(SessionStates.ACTIVE, currentSessionId);
      } else {
        currentSessionId = null;
        updateSessionUI(SessionStates.NO_SESSION);
        if (currentPage !== "home-section") navigate("home-section");
      }
    }
  });
});
