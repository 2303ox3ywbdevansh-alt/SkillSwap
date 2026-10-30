(() => {
  const root = document.getElementById("video-room");
  if (!root) return;
  if (typeof io !== "function") {
    const message = document.getElementById("call-status");
    if (message) {
      message.textContent = "The video call client could not load. Check your internet connection and reload this page.";
      message.classList.add("is-error");
    }
    const button = document.getElementById("join-call");
    if (button) button.disabled = true;
    return;
  }

  const sessionId = Number(root.dataset.sessionId);
  const userId = Number(root.dataset.userId);
  const socket = io();
  const status = document.getElementById("call-status");
  const joinButton = document.getElementById("join-call");
  const leaveButton = document.getElementById("leave-call");
  const micButton = document.getElementById("toggle-mic");
  const cameraButton = document.getElementById("toggle-camera");
  const localVideo = document.getElementById("local-video");
  const remoteVideo = document.getElementById("remote-video");
  const localPlaceholder = document.getElementById("local-placeholder");
  const remotePlaceholder = document.getElementById("remote-placeholder");
  const rtcConfig = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };

  let joined = false;
  let localStream = null;
  let peerConnection = null;
  let peerId = null;
  let peerReady = false;
  let makingOffer = false;
  let pendingCandidates = [];

  function setStatus(message, isError = false) {
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  }

  function closePeer() {
    if (peerConnection) {
      peerConnection.ontrack = null;
      peerConnection.onicecandidate = null;
      peerConnection.close();
      peerConnection = null;
    }
    remoteVideo.srcObject = null;
    remotePlaceholder.hidden = false;
    pendingCandidates = [];
  }

  function ensurePeerConnection() {
    if (peerConnection) return peerConnection;
    peerConnection = new RTCPeerConnection(rtcConfig);
    if (localStream) localStream.getTracks().forEach((track) => peerConnection.addTrack(track, localStream));
    peerConnection.ontrack = (event) => {
      remoteVideo.srcObject = event.streams[0];
      remotePlaceholder.hidden = true;
    };
    peerConnection.onicecandidate = (event) => {
      if (event.candidate && joined) {
        socket.emit("video:ice", { session_id: sessionId, data: event.candidate.toJSON() });
      }
    };
    peerConnection.onconnectionstatechange = () => {
      const state = peerConnection?.connectionState;
      if (state === "connected") setStatus("Your call is connected.");
      else if (state === "failed") setStatus("Could not connect. Try again or check your network.", true);
      else if (state === "disconnected") setStatus("Call connection interrupted. Trying to reconnect…");
    };
    return peerConnection;
  }

  async function flushCandidates() {
    if (!peerConnection?.remoteDescription) return;
    const candidates = pendingCandidates;
    pendingCandidates = [];
    for (const candidate of candidates) await peerConnection.addIceCandidate(candidate);
  }

  async function maybeOffer() {
    if (!joined || !localStream || !peerReady || peerId === null || userId > peerId || makingOffer) return;
    makingOffer = true;
    try {
      const pc = ensurePeerConnection();
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      socket.emit("video:offer", { session_id: sessionId, data: pc.localDescription.toJSON() });
      setStatus("Calling your session partner…");
    } catch (error) {
      setStatus("Could not start the call: " + error.message, true);
    } finally {
      makingOffer = false;
    }
  }

  function enterRoom() {
    socket.emit("video:join", { session_id: sessionId }, (reply) => {
      if (!reply?.ok) {
        setStatus(reply?.error || "Could not join the session room.", true);
        return;
      }
      joined = true;
      setStatus("Room ready. Join the call when you're ready.");
    });
  }
  socket.on("connect", enterRoom);

  socket.on("connect_error", () => setStatus("Connection failed. Refresh the page and try again.", true));
  socket.on("video:peer_joined", (peer) => {
    if (!peer || peer.user_id === userId) return;
    peerId = Number(peer.user_id);
    if (localStream) socket.emit("video:ready", { session_id: sessionId });
  });
  socket.on("video:ready", (peer) => {
    if (!peer || peer.user_id === userId) return;
    peerId = Number(peer.user_id);
    peerReady = true;
    setStatus("Your partner is ready. Connecting the call…");
    maybeOffer();
  });
  socket.on("video:offer", async (message) => {
    try {
      peerId = Number(message.user_id);
      const pc = ensurePeerConnection();
      await pc.setRemoteDescription(message.data);
      await flushCandidates();
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      socket.emit("video:answer", { session_id: sessionId, data: pc.localDescription.toJSON() });
      setStatus("Answering your session partner…");
    } catch (error) {
      setStatus("Could not answer the call: " + error.message, true);
    }
  });
  socket.on("video:answer", async (message) => {
    try {
      peerId = Number(message.user_id);
      if (!peerConnection) return;
      await peerConnection.setRemoteDescription(message.data);
      await flushCandidates();
    } catch (error) {
      setStatus("Could not connect the call: " + error.message, true);
    }
  });
  socket.on("video:ice", async (message) => {
    try {
      const candidate = new RTCIceCandidate(message.data);
      if (peerConnection?.remoteDescription) await peerConnection.addIceCandidate(candidate);
      else pendingCandidates.push(candidate);
    } catch (error) {
      setStatus("A network connection candidate failed: " + error.message, true);
    }
  });
  socket.on("video:peer_left", () => {
    peerId = null;
    peerReady = false;
    closePeer();
    setStatus("Your partner left the call. You can keep waiting or leave.");
  });

  joinButton.addEventListener("click", async () => {
    if (!joined) {
      setStatus("Reconnecting to the session room…");
      if (socket.connected) enterRoom();
      else socket.connect();
      return;
    }
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      localVideo.srcObject = localStream;
      localPlaceholder.hidden = true;
      ensurePeerConnection();
      joinButton.disabled = true;
      leaveButton.disabled = false;
      micButton.disabled = false;
      cameraButton.disabled = false;
      setStatus("Camera and microphone are on. Waiting for your partner…");
      socket.emit("video:ready", { session_id: sessionId });
      maybeOffer();
    } catch (error) {
      setStatus("Camera/microphone access failed: " + error.message, true);
    }
  });

  micButton.addEventListener("click", () => {
    const track = localStream?.getAudioTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    micButton.textContent = track.enabled ? "Mute mic" : "Unmute mic";
  });
  cameraButton.addEventListener("click", () => {
    const track = localStream?.getVideoTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    cameraButton.textContent = track.enabled ? "Turn camera off" : "Turn camera on";
  });
  leaveButton.addEventListener("click", () => {
    socket.emit("video:leave");
    closePeer();
    if (localStream) localStream.getTracks().forEach((track) => track.stop());
    localStream = null;
    localVideo.srcObject = null;
    localPlaceholder.hidden = false;
    peerId = null;
    peerReady = false;
    joined = false;
    joinButton.disabled = false;
    leaveButton.disabled = true;
    micButton.disabled = true;
    cameraButton.disabled = true;
    micButton.textContent = "Mute mic";
    cameraButton.textContent = "Turn camera off";
    setStatus("You left the call.");
  });
  window.addEventListener("pagehide", () => socket.emit("video:leave"));
})();


