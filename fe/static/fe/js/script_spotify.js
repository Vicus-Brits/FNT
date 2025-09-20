// AUTO-PLAY FEATURE
let lastAutoPlayTrackId = null;
let autoPlayInterval = null; // timer for checking playback
let lastKnownTrack = null; // remember last song
let autoPlayEnabled = false; // auto-play on/of
let autoPlayInProgress = false; // stops double-triggering

// HELPERS
// Spotify button state
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
    button.innerHTML = "Disconnect";
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
    // Add session_id to URL if not already present and we have a current session
    if (currentSessionId && !url.includes("session_id=")) {
      const separator = url.includes("?") ? "&" : "?";
      url = `${url}${separator}session_id=${currentSessionId}`;
    }

    const response = await fetch(url, options);
    // If 401 (unauthorized), refresh token
    if (response.status === 401) {
      console.log("Token expired");

      if (!currentSessionId) {
        console.log("No session ID for refresh");
        return response;
      }

      // refresh the token
      const refreshResponse = await fetch("/spotify/refresh/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ session_id: currentSessionId }),
      });

      if (refreshResponse.ok) {
        console.log("Token refreshed");
        // Retry original request
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
  // disconnect if connected
  if (spotifyConnected) {
    await disconnectSpotify();
    return;
  }

  try {
    updateSpotifyButtonState("connecting");

    const statusDiv = document.getElementById("spotifyStatus");
    showSpinner(statusDiv, "Redirecting to Spotify...");

    // Check if we have a session
    if (!currentSessionId) {
      throw new Error("No active session. Please create a session first.");
    }

    //Spotify authorization URL with session_id
    const response = await fetch(
      `/spotify/auth/?format=json&session_id=${currentSessionId}`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
      }
    );

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
    console.error("Error:", error);

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
    const controlsDiv = document.getElementById("spotifyControls");
    showSpinner(statusDiv, "Disconnecting from Spotify...");

    // clear tokens
    const response = await fetch("/spotify/disconnect/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ session_id: currentSessionId }),
    });

    spotifyConnected = false;
    updateSpotifyButtonState("disconnected");

    // hide control buttons
    if (controlsDiv) {
      controlsDiv.style.display = "none";
    }

    // Clear status
    if (statusDiv) {
      statusDiv.innerHTML = "";
    }

    // Stop auto-play when disconnecting
    stopAutoPlay();

    console.log("Disconnected");
  } catch (error) {
    console.error("Error:", error);

    spotifyConnected = false;
    updateSpotifyButtonState("disconnected");

    const controlsDiv = document.getElementById("spotifyControls");
    // Hide control buttons on error too
    if (controlsDiv) {
      controlsDiv.style.display = "none";
    }

    // Stop auto-play on disconnect error
    stopAutoPlay();

    const statusDiv = document.getElementById("spotifyStatus");
    if (statusDiv) {
      showError(statusDiv, `Error: ${error.message}`);
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
              : '<div class="bg-secondary rounded d-flex align-items-center justify-content-center" style="width: 150px; height: 150px;"><span class="text-light">No Image</span></div>'
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
        No track information available
      </div>
    `;
    section.style.display = "block";
  }
}

// Get Spotify user profile information
async function getSpotifyUserProfile() {
  try {
    const response = await makeSpotifyRequest("/spotify/user-profile/", {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching user profile:", error);
    return { error: error.message };
  }
}

// Get Spotify devices and find active device
async function getSpotifyDevices() {
  try {
    const response = await makeSpotifyRequest("/spotify/devices/", {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching devices:", error);
    return { error: error.message };
  }
}

// Display user info and active device when connected
async function displaySpotifyUserInfo() {
  const statusDiv = document.getElementById("spotifyStatus");
  const controlsDiv = document.getElementById("spotifyControls");

  try {
    // Show control buttons when connected
    if (controlsDiv) {
      controlsDiv.style.display = "block";
    }

    // Show loading state
    showSpinner(statusDiv, "Loading user information...");

    // Get user profile, devices, and currently playing in parallel
    const [userProfile, devices, currentlyPlaying] = await Promise.all([
      getSpotifyUserProfile(),
      getSpotifyDevices(),
      getCurrentlyPlaying(),
    ]);

    let userInfoHtml = "";

    // Add currently playing section at the top
    if (currentlyPlaying && !currentlyPlaying.error) {
      if (
        currentlyPlaying.message &&
        currentlyPlaying.message.includes("Nothing currently playing")
      ) {
        userInfoHtml += `
          <div class="alert alert-secondary mb-3">
            <div class="text-center">
              <h6>Nothing Currently Playing</h6>
              <p class="mb-0 text-muted">No music is playing on Spotify</p>
            </div>
          </div>
        `;
      } else if (currentlyPlaying.item) {
        const track = currentlyPlaying.item;
        const artists = track.artists
          ? track.artists.map((artist) => artist.name).join(", ")
          : "Unknown Artist";
        const album = track.album ? track.album.name : "Unknown Album";
        const isPlaying = currentlyPlaying.is_playing;
        const progress = currentlyPlaying.progress_ms || 0;
        const duration = track.duration_ms || 0;

        // Format time in MM:SS
        const formatTime = (ms) => {
          const minutes = Math.floor(ms / 60000);
          const seconds = Math.floor((ms % 60000) / 1000);
          return `${minutes}:${seconds.toString().padStart(2, "0")}`;
        };

        const progressPercent = duration > 0 ? (progress / duration) * 100 : 0;

        userInfoHtml += `
          <div class="card mb-3">
            <div class="card-header bg-spotify text-white">
              <h6 class="mb-0">
                ${isPlaying ? "Now Playing" : "Paused"}
              </h6>
            </div>
            <div class="card-body">
              <div class="row">
                <div class="col-md-3 text-center">
                  ${
                    track.album &&
                    track.album.images &&
                    track.album.images.length > 0
                      ? `<img src="${track.album.images[0].url}" alt="Album Cover" class="img-fluid rounded shadow" style="max-width: 120px;">`
                      : '<div class="bg-secondary rounded d-flex align-items-center justify-content-center mx-auto" style="width: 120px; height: 120px;"><span class="text-light">No Image</span></div>'
                  }
                </div>
                <div class="col-md-9">
                  <h5 class="mb-2">${track.name}</h5>
                  <p class="mb-1 text-muted">
                    <strong>Artist:</strong> ${artists}
                  </p>
                  <p class="mb-3 text-muted">
                    <strong>Album:</strong> ${album}
                  </p>
                </div>
              </div>
            </div>
          </div>
        `;
      }
    } else {
      userInfoHtml += `
        <div class="alert alert-warning mb-3">
          Unable to load currently playing information
        </div>
      `;
    }

    // Add Refresh button after currently playing section
    userInfoHtml += `
      <div class="text-center mb-3">
        <button id="refreshSpotifyBtn" class="btn btn-outline-spotify btn-lg px-4 py-2" onclick="displaySpotifyUserInfo()">
          Refresh
        </button>
      </div>
    `;

    // Add user and device info section at the bottom
    userInfoHtml += '<div class="alert alert-dark">';

    // Add user name if available
    if (userProfile && !userProfile.error) {
      const displayName =
        userProfile.display_name || userProfile.id || "Spotify User";
      userInfoHtml += `
        <div class="mb-2">
          <strong>Connected as:</strong> ${displayName}
        </div>
      `;
    }

    // Add active device info if available
    if (devices && !devices.error && devices.devices) {
      const activeDevice = devices.devices.find((device) => device.is_active);

      if (activeDevice) {
        userInfoHtml += `
          <div class="mb-2">
            <strong>Active Device:</strong> ${activeDevice.name}
          </div>
        `;
      } else if (devices.devices.length > 0) {
        userInfoHtml += `
          <div class="mb-2">
            <strong>No Active Device</strong> - Please open Spotify on a device
          </div>
        `;
      } else {
        userInfoHtml += `
          <div class="mb-2">
            <strong>No Devices Found</strong> - Please open Spotify on a device
          </div>
        `;
      }
    }

    userInfoHtml += "</div>";

    statusDiv.innerHTML = userInfoHtml;

    // Start auto-play monitoring when user info is displayed
    startAutoPlay();
  } catch (error) {
    console.error("Error displaying user info:", error);
    statusDiv.innerHTML = `
      <div class="alert alert-warning">
        Unable to load user information: ${error.message}
      </div>
    `;
  }
}

// Check if user is already connected to Spotify (for page refresh)
async function checkSpotifyConnection() {
  try {
    const response = await fetch(
      `/spotify/user-profile/?session_id=${currentSessionId}`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
      }
    );

    if (response.ok) {
      // User is connected
      spotifyConnected = true;
      updateSpotifyButtonState("connected");

      // Show control buttons when connected
      const controlsDiv = document.getElementById("spotifyControls");
      if (controlsDiv) {
        controlsDiv.style.display = "block";
      }

      // If we're on the spotify section, show user info
      if (currentPage === "spotify-section") {
        displaySpotifyUserInfo();
      }

      return true;
    } else {
      // User is not connected
      spotifyConnected = false;
      updateSpotifyButtonState("disconnected");

      // Hide control buttons when not connected
      const controlsDiv = document.getElementById("spotifyControls");
      if (controlsDiv) {
        controlsDiv.style.display = "none";
      }

      // Stop auto-play when not connected
      stopAutoPlay();

      return false;
    }
  } catch (error) {
    // Error means not connected
    spotifyConnected = false;
    updateSpotifyButtonState("disconnected");

    // Hide control buttons on error
    const controlsDiv = document.getElementById("spotifyControls");
    if (controlsDiv) {
      controlsDiv.style.display = "none";
    }

    stopAutoPlay();

    return false;
  }
}

// Check for Spotify callback parameters on page load
function checkSpotifyCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const spotifyStatus = urlParams.get("spotify");
  const error = urlParams.get("error");

  if (spotifyStatus === "connected") {
    const controlsDiv = document.getElementById("spotifyControls");

    // set connected
    spotifyConnected = true;
    updateSpotifyButtonState("connected");

    // Show control buttons
    if (controlsDiv) {
      controlsDiv.style.display = "block";
    }

    // Clean up URL
    window.history.replaceState({}, document.title, window.location.pathname);

    navigate("spotify-section");

    // user info and active device
    displaySpotifyUserInfo();

    // handle error
  } else if (error) {
    const statusDiv = document.getElementById("spotifyStatus");
    const errorMessage = `Error: ${error}`;

    // Show error message
    statusDiv.innerHTML = `
      <div class="alert alert-danger">
        <h6>Connection Failed</h6>
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

async function playNextSong() {
  const nextBtn = document.getElementById("nextBtn");
  if (!nextBtn) return;
  const originalContent = nextBtn.innerHTML;

  try {
    // load spinner
    nextBtn.disabled = true;
    nextBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> <span class="d-none d-sm-inline ms-1">Playing...</span>';

    // call our API to move to the next song
    const response = await fetch("/api/next-song/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        session_id: currentSessionId,
      }),
    });

    const data = await response.json();

    // lets hope that worked and update the UI
    if (response.ok && data.success) {
      console.log("Next song playing:", data.message);

      // refresh Spotify info
      displaySpotifyUserInfo();

      // success message song title and artist
      const statusDiv = document.getElementById("spotifyStatus");
      const successDiv = document.createElement("div");
      successDiv.className = "alert alert-success mt-2";
      successDiv.innerHTML = `<strong>Now Playing:</strong> ${data.song.title} by ${data.song.artist}`;
      statusDiv.appendChild(successDiv);
      // remove msg after 5 seconds
      setTimeout(() => {
        if (successDiv.parentNode)
          successDiv.parentNode.removeChild(successDiv);
      }, 5000);
    } else {
      // TODO: Handle case when spotify cannot find song
      alert("Please press Next in the Spotify Player");
      console.log("Error:", data);
    }
  } catch (e) {
    alert("Please press Next in the Spotify Player");
    console.log("playNextSong error:", e);
  } finally {
    // return button state
    nextBtn.disabled = false;
    nextBtn.innerHTML = originalContent;
  }
}

// auto-play function for continious playback
function startAutoPlay() {
  // if running, return
  if (autoPlayInterval || !spotifyConnected) {
    return;
  }

  console.log("Starting auto-play...");
  autoPlayEnabled = true;

  // check for song end (2 sec interval)
  autoPlayInterval = setInterval(checkForSongEnd, 2000);
  setTimeout(checkForSongEnd, 1000);
}

// stop the auto-play feature
function stopAutoPlay() {
  // stop if running
  if (autoPlayInterval) {
    console.log("Stopping auto-play...");
    clearInterval(autoPlayInterval); // stop timer
    autoPlayInterval = null;
    autoPlayEnabled = false;
    lastKnownTrack = null;
    autoPlayInProgress = false; // reset flag
  }
}

//  if current song is near end -> play the next one
async function checkForSongEnd() {
  // checks
  if (!autoPlayEnabled || !spotifyConnected || !currentSessionId) {
    return;
  }

  try {
    // get current playback info
    const currentData = await getCurrentlyPlaying();
    if (!currentData || !currentData.item) {
      // If Spotify says nothing, play next
      if (autoPlayEnabled && spotifyConnected && currentSessionId) {
        await autoPlayNextSong();
      }
      return;
    }

    const currentTrack = currentData.item;
    const progress = currentData.progress_ms || 0;
    const duration = currentTrack.duration_ms || 0;
    const isPlaying = currentData.is_playing;

    // check if new track
    const trackId = currentTrack.id;
    const trackChanged = lastKnownTrack && lastKnownTrack.id !== trackId;

    // set current track
    lastKnownTrack = {
      id: trackId,
      name: currentTrack.name,
      artists: currentTrack.artists?.map((a) => a.name).join(", ") || "Unknown",
      progress: progress,
      duration: duration,
    };

    if (trackChanged) {
      lastAutoPlayTrackId = null; // clear debounce so new song is immediately eligible
      return;
    }

    const timeRemaining = duration - progress;
    const isNearEnd = timeRemaining <= 3000;
    const isVeryNearEnd = timeRemaining <= 1500;
    if (
      currentData.is_playing &&
      isVeryNearEnd &&
      lastAutoPlayTrackId !== trackId
    ) {
      lastAutoPlayTrackId = trackId; // one trigger per track
      await autoPlayNextSong(trackId); // pass previous track id
      return;
    }

    // if ending and still playing -> next song
    if (isVeryNearEnd && isPlaying) {
      await autoPlayNextSong();
      return;
    }

    // if close to end and playing -> next song
    if (isNearEnd && isPlaying) {
      const waitTime = Math.max(timeRemaining - 500, 500); // wait until ~500ms before end
      setTimeout(async () => {
        if (!autoPlayEnabled || !spotifyConnected) return;
        await autoPlayNextSong();
      }, waitTime);
    }
  } catch (e) {
    // TODO: consider how we get here and handle
    console.error("Consider how we get here and handle:", e);
    return;
  }
}

async function ensureNextIsPlaying(prevTrackId) {
  for (let i = 0; i < 4; i++) {
    const cur = await getCurrentlyPlaying();
    if (cur && cur.item) {
      const sameTrack = prevTrackId && cur.item.id === prevTrackId;
      if (!sameTrack && cur.is_playing) return true; // success
      if (!sameTrack && !cur.is_playing) {
        try {
          const stateResp = await makeSpotifyRequest(
            "/spotify/playback-state/"
          );
          const stateData = await stateResp.json();
          const deviceId = stateData?.device?.id;
          const playUrl =
            "/spotify/play/" + (deviceId ? `?device_id=${deviceId}` : "");

          await makeSpotifyRequest(playUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCSRFToken(),
            },
          });
        } catch (e) {}
      }
    }
    await waitMs(500);
  }
  return false;
}

function waitMs(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

async function autoPlayNextSong(prevTrackId) {
  if (!autoPlayEnabled || !spotifyConnected || !currentSessionId) return;
  if (autoPlayInProgress) return;
  autoPlayInProgress = true;
  try {
    setRepeatOff(); // best effort
    const response = await fetch("/api/next-song/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ session_id: currentSessionId }),
    });
    const data = await response.json();
    if (response.ok && data && data.success) {
      await waitMs(700); // gap to ensure updates have time
      const ok = await ensureNextIsPlaying(prevTrackId);
      if (!ok) {
        // start playback if stalled
        try {
          const stateResp = await makeSpotifyRequest(
            "/spotify/playback-state/"
          );
          const stateData = await stateResp.json();
          const deviceId = stateData?.device?.id;
          const playUrl =
            "/spotify/play/" + (deviceId ? `?device_id=${deviceId}` : "");

          await makeSpotifyRequest(playUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCSRFToken(),
            },
          });
        } catch (e) {}
      }
      // refresh screen
      setTimeout(() => displaySpotifyUserInfo(), 1200);
    } else {
      if (data && data.error && data.error.includes("No songs in playlist")) {
        stopAutoPlay();
      }
    }
  } finally {
    autoPlayInProgress = false;
  }
}

// if connected to spotify start auto-play
function enableAutoPlayOnConnection() {
  if (spotifyConnected && currentPage === "spotify-section") {
    startAutoPlay();
  }
}

// pause player
async function pauseSpotifyPlayback() {
  const pauseBtn = document.getElementById("pauseBtn");
  const originalContent = pauseBtn.innerHTML;

  try {
    if (!spotifyConnected) {
      alert("Please connect to Spotify first.");
      return;
    }

    // show that the button is busy
    pauseBtn.disabled = true;
    pauseBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> <span class="d-none d-sm-inline ms-1">Pausing...</span>';

    // call pause api
    const response = await makeSpotifyRequest("/spotify/pause/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
    });

    const data = await response.json();

    console.log("Paused playback");

    // update the UI so it shows the paused state
    displaySpotifyUserInfo();

    // user  pop up message
    const statusDiv = document.getElementById("spotifyStatus");
    if (statusDiv) {
      const pauseDiv = document.createElement("div");
      pauseDiv.className = "alert alert-secondary mt-2";
      pauseDiv.innerHTML = `<i class="fas fa-pause me-1"></i> Playback paused`;
      statusDiv.appendChild(pauseDiv);
      setTimeout(() => {
        if (pauseDiv.parentNode) pauseDiv.parentNode.removeChild(pauseDiv);
      }, 3000);
    }
  } catch (e) {
    alert("Something went wrong while pausing.");
  } finally {
    // reset button
    pauseBtn.disabled = false;
    pauseBtn.innerHTML = originalContent;
  }
}
async function playSpotifyPlayback() {
  const playBtn = document.getElementById("playBtn");
  if (!playBtn) return; // if the button doesn't exist, just stop
  const originalContent = playBtn.innerHTML;

  try {
    if (!spotifyConnected) {
      alert("Please connect to Spotify first.");
      return;
    }

    // if playing, do nothing
    const currentState = await getCurrentlyPlaying();
    if (currentState && currentState.is_playing) {
      console.log("Already playing, ignoring play button press");
      return;
    }

    // button busy
    playBtn.disabled = true;
    playBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> <span class="d-none d-sm-inline ms-1">Playing...</span>';

    // call play api
    const response = await makeSpotifyRequest("/spotify/play/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
    });

    const data = await response.json();

    console.log("Playback started");

    // update screens
    displaySpotifyUserInfo();

    // user pop up message
    const statusDiv = document.getElementById("spotifyStatus");
    if (statusDiv) {
      const playDiv = document.createElement("div");
      playDiv.className = "alert alert-success mt-2";
      playDiv.innerHTML = `<i class="fas fa-play me-1"></i> Playback resumed`;
      statusDiv.appendChild(playDiv);

      setTimeout(() => {
        if (playDiv.parentNode) playDiv.parentNode.removeChild(playDiv);
      }, 3000);
    }
  } catch (e) {
    alert("Something went wrong.");
  } finally {
    // reset button
    playBtn.disabled = false;
    playBtn.innerHTML = originalContent;
  }
}

// helper

async function setRepeatOff() {
  try {
    await makeSpotifyRequest("/spotify/repeat-off/", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
    });
  } catch (e) {
    /* TODO: Handle error */
  }
}
