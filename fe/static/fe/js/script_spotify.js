// HELPERS
// Spotify button state based on connection status
function updateSpotifyButtonState(state) {
  const button = document.getElementById("startSpotifyBtn");
  const description = document.querySelector(
    "#spotify-section .card-text.text-muted"
  );

  if (state === "connecting") {
    button.disabled = true;
    button.innerHTML =
      '<i class="fa fa-spinner fa-spin me-2"></i>Connecting...';
    button.className = "btn btn-spotify btn-lg px-5 py-3";
    if (description) description.style.display = "block";
  } else if (state === "connected") {
    button.disabled = false;
    button.innerHTML = '<i class="fas fa-check me-2"></i>Disconnect';
    button.className = "btn btn-success btn-lg px-5 py-3";
    if (description) description.style.display = "none";
  } else {
    button.disabled = false;
    button.innerHTML = '<i class="fab fa-spotify me-2"></i>Connect to Spotify';
    button.className = "btn btn-spotify btn-lg px-5 py-3";
    if (description) description.style.display = "block";
  }
}
// make Spotify requests, refresh token on failure
async function makeSpotifyRequest(url, options = {}) {
  try {
    const response = await fetch(url, options);
    // If 401 (unauthorized), refresh token
    if (response.status === 401) {
      console.log("Token expired");
      // refresh the token
      const refreshResponse = await fetch("/spotify/refresh/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
      });

      if (refreshResponse.ok) {
        console.log("Token refreshed");
        // Retry  request
        const retryResponse = await fetch(url, options);
        return retryResponse;
      } else {
        console.log("Token refresh failed");
        return response;
      }
    }
    return response;
  } catch (error) {
    throw error;
  }
}

// SPOTIFY INTEGRATION
async function startSpotifyAuth() {
  if (spotifyConnected) {
    await disconnectSpotify();
    return;
  }

  try {
    updateSpotifyButtonState("connecting");

    const statusDiv = document.getElementById("spotifyStatus");
    showSpinner(statusDiv, "Redirecting to Spotify...");

    //Spotify authorization URL
    const response = await fetch("/spotify/auth/?format=json", {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch (jsonError) {
        errorData = null;
      }

      const errorMessage =
        errorData?.error || `HTTP error! status: ${response.status}`;
      throw new Error(errorMessage);
    }

    const data = await response.json();

    if (data.authorization_url) {
      // redirect the user
      window.location.href = data.authorization_url;
    } else {
      throw new Error("No authorization URL received");
    }
  } catch (error) {
    console.error("Error starting Spotify auth:", error);

    const statusDiv = document.getElementById("spotifyStatus");
    showError(statusDiv, `Error: ${error.message}`);
    updateSpotifyButtonState("disconnected");
  }
}

// Disconnect from Spotify
async function disconnectSpotify() {
  try {
    updateSpotifyButtonState("connecting");

    const statusDiv = document.getElementById("spotifyStatus");
    showSpinner(statusDiv, "Disconnecting from Spotify...");

    // clear tokens
    const response = await fetch("/spotify/disconnect/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
    });

    spotifyConnected = false;
    updateSpotifyButtonState("disconnected");

    // Clear status
    if (statusDiv) {
      statusDiv.innerHTML = "";
    }

    console.log("Disconnected");
  } catch (error) {
    console.error("Error:", error);

    spotifyConnected = false;
    updateSpotifyButtonState("disconnected");

    const statusDiv = document.getElementById("spotifyStatus");
    if (statusDiv) {
      showError(statusDiv, `Disconnect failed: ${error.message}`);
    }
  }
}

// Get currently playing song information with automatic token refresh
async function getCurrentlyPlaying() {
  try {
    const response = await makeSpotifyRequest("/spotify/currently-playing/", {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    });

    if (response.status === 204) {
      return { message: "Nothing currently playing" };
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      const errorInfo = {
        status: response.status,
        message: errorData?.error || "Unknown error",
        details: errorData?.details || response.statusText,
      };

      // error handling (improve with details)
      let userMessage = errorInfo.message;
      throw new Error(userMessage);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error:", error);
    return { error: error.message, status: error.status };
  }
}

// Playing song (current)
function displayCurrentlyPlaying(data) {
  const section = document.getElementById("currentlyPlayingSection");
  const content = document.getElementById("currentlyPlayingContent");

  if (!section || !content) {
    console.error("No Song Found");
    return;
  }

  if (data.error) {
    content.innerHTML = `
      <div class="alert alert-warning">
        <i class="fas fa-exclamation-triangle me-2"></i>
        Error: ${data.error}
      </div>
    `;
    section.style.display = "block";
    return;
  }
  //prompt user to play something
  if (data.message && data.message.includes("Nothing currently playing")) {
    content.innerHTML = `
      <div class="alert alert-info">
        <i class="fas fa-pause me-2"></i>
        Nothing is currently playing on Spotify
      </div>
    `;
    section.style.display = "block";
    return;
  }

  if (data.item) {
    const track = data.item;
    const artists = track.artists
      ? track.artists.map((artist) => artist.name).join(", ")
      : "Unknown Artist";
    const album = track.album ? track.album.name : "Unknown Album";
    const isPlaying = data.is_playing;
    const progress = data.progress_ms || 0;
    const duration = track.duration_ms || 0;

    // Format time in MM:SS
    const formatTime = (ms) => {
      const minutes = Math.floor(ms / 60000);
      const seconds = Math.floor((ms % 60000) / 1000);
      return `${minutes}:${seconds.toString().padStart(2, "0")}`;
    };

    const progressPercent = duration > 0 ? (progress / duration) * 100 : 0;

    content.innerHTML = `
      <div class="row">
        <div class="col-md-3 mb-3">
          ${
            track.album && track.album.images && track.album.images.length > 0
              ? `<img src="${track.album.images[0].url}" alt="Album Cover" class="img-fluid rounded" style="max-width: 150px;">`
              : '<div class="bg-secondary rounded d-flex align-items-center justify-content-center" style="width: 150px; height: 150px;"><i class="fas fa-music text-light fa-2x"></i></div>'
          }
        </div>
        <div class="col-md-9">
          <h5 class="mb-1">${track.name}</h5>
          <p class="mb-1 text-muted">by ${artists}</p>
          <p class="mb-2 small text-muted">from ${album}</p>
          
          <div class="mb-2">
            <div class="d-flex justify-content-between align-items-center">
              <span class="small">${formatTime(progress)}</span>
              <span class="small">${formatTime(duration)}</span>
            </div>
            <div class="progress" style="height: 4px;">
              <div class="progress-bar bg-spotify" role="progressbar" style="width: ${progressPercent}%"></div>
            </div>
          </div>
          
          <div class="d-flex align-items-center">
            <span class="badge ${
              isPlaying ? "bg-success" : "bg-secondary"
            } me-2">
              <i class="fas ${isPlaying ? "fa-play" : "fa-pause"} me-1"></i>
              ${isPlaying ? "Playing" : "Paused"}
            </span>
            <small class="text-muted">Last updated: ${new Date().toLocaleTimeString()}</small>
          </div>
        </div>
      </div>
    `;
    section.style.display = "block";
  } else {
    content.innerHTML = `
      <div class="alert alert-info">
        <i class="fas fa-info-circle me-2"></i>
        No track information available
      </div>
    `;
    section.style.display = "block";
  }
}

// Check Spotify callback parameters
function checkSpotifyCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const spotifyStatus = urlParams.get("spotify");
  const error = urlParams.get("error");

  if (spotifyStatus === "connected") {
    const statusDiv = document.getElementById("spotifyStatus");

    // Mark as connected
    spotifyConnected = true;

    // Update button state to reflect connection
    updateSpotifyButtonState("connected");

    // Clean up URL parameters
    window.history.replaceState({}, document.title, window.location.pathname);

    // Redirect to Spotify section after successful connection
    navigate("spotify-section");
  } else if (error) {
    const statusDiv = document.getElementById("spotifyStatus");
    const errorMessage = `Error: ${error}`;

    // Show error message
    statusDiv.innerHTML = `
      <div class="alert alert-danger">
        <h6><i class="fas fa-exclamation-circle me-2"></i>Connection Failed</h6>
        <p class="mb-0">${errorMessage}</p>
        <p class="mb-0 mt-2"><small>Please try connecting again.</small></p>
      </div>
    `;

    // Update button state back to disconnected
    updateSpotifyButtonState("disconnected");

    // Clean up URL parameters
    window.history.replaceState({}, document.title, window.location.pathname);
  }
}

// Call on page load
document.addEventListener("DOMContentLoaded", function () {
  // This is handled in the main DOMContentLoaded listener above
});
