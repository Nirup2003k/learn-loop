document.addEventListener('DOMContentLoaded', () => {
    const localVideo = document.getElementById('local-video');
    const remoteVideo = document.getElementById('remote-video');
    const waitingMessage = document.getElementById('waitingMessage');
    
    const btnMic = document.getElementById('btn-toggle-mic');
    const btnCam = document.getElementById('btn-toggle-cam');
    const btnEnd = document.getElementById('btn-end-call');

    let localStream;
    let peerConnection;
    let signalingSocket;
    
    const ICE_SERVERS = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ]
    };

    const roomNameElement = document.getElementById('room-name');
    const ROOM_NAME = roomNameElement ? JSON.parse(roomNameElement.textContent) : '';
    const WS_SCHEME = window.location.protocol === "https:" ? "wss" : "ws";

    // Initialize WebRTC
    async function startWebRTC() {
        try {
            // Get local media
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            localVideo.srcObject = localStream;
            
            // Connect to Signaling Server via WebSocket
            const wsUrl = `${WS_SCHEME}://${window.location.host}/ws/video/${ROOM_NAME}/`;
            signalingSocket = new WebSocket(wsUrl);

            signalingSocket.onopen = () => {
                console.log("Connected to signaling server");
                // The first user to join will create the offer when the second user joins. 
                // For simplicity, we broadcast a "joined" message.
                signalingSocket.send(JSON.stringify({
                    'message': { 'type': 'joined' }
                }));
            };

            signalingSocket.onmessage = async (e) => {
                const data = JSON.parse(e.data);
                const message = data.message;
                
                if (message.type === 'joined') {
                    // Someone joined, we should initiate the call by sending an offer
                    createOffer();
                } else if (message.type === 'offer') {
                    handleOffer(message.offer);
                } else if (message.type === 'answer') {
                    handleAnswer(message.answer);
                } else if (message.type === 'ice-candidate') {
                    handleIceCandidate(message.candidate);
                } else if (message.type === 'user-left') {
                    endCallLocally();
                }
            };
            
        } catch (error) {
            console.error("Error accessing media devices.", error);
            alert("Could not access Camera or Microphone.");
        }
    }

    function createPeerConnection() {
        peerConnection = new RTCPeerConnection(ICE_SERVERS);

        // Add local tracks to peer connection
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });

        // Listen for remote tracks
        peerConnection.ontrack = (event) => {
            waitingMessage.style.display = 'none'; // Hide waiting text
            remoteVideo.srcObject = event.streams[0];
        };

        // Listen for ICE candidates to send to peer
        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                signalingSocket.send(JSON.stringify({
                    'message': {
                        'type': 'ice-candidate',
                        'candidate': event.candidate
                    }
                }));
            }
        };
    }

    async function createOffer() {
        createPeerConnection();
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        
        signalingSocket.send(JSON.stringify({
            'message': {
                'type': 'offer',
                'offer': offer
            }
        }));
    }

    async function handleOffer(offer) {
        createPeerConnection();
        await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
        
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        
        signalingSocket.send(JSON.stringify({
            'message': {
                'type': 'answer',
                'answer': answer
            }
        }));
    }

    async function handleAnswer(answer) {
        if (!peerConnection.currentRemoteDescription) {
            await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
        }
    }

    async function handleIceCandidate(candidate) {
        if (peerConnection) {
            await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
        }
    }

    function endCallLocally() {
        if (peerConnection) {
            peerConnection.close();
            peerConnection = null;
        }
        remoteVideo.srcObject = null;
        waitingMessage.style.display = 'block';
        waitingMessage.innerHTML = '<h3>Call Ended</h3><p>The other user has left.</p>';
    }

    // --- UI Controls ---

    btnMic.addEventListener('click', () => {
        const audioTrack = localStream.getAudioTracks()[0];
        if (audioTrack) {
            audioTrack.enabled = !audioTrack.enabled;
            btnMic.classList.toggle('active', !audioTrack.enabled);
        }
    });

    btnCam.addEventListener('click', () => {
        const videoTrack = localStream.getVideoTracks()[0];
        if (videoTrack) {
            videoTrack.enabled = !videoTrack.enabled;
            btnCam.classList.toggle('active', !videoTrack.enabled);
            // Gray out local video slightly
            localVideo.style.opacity = videoTrack.enabled ? '1' : '0.3';
        }
    });

    btnEnd.addEventListener('click', () => {
        if (signalingSocket) {
            signalingSocket.send(JSON.stringify({
                'message': { 'type': 'user-left' }
            }));
        }
        endCallLocally();
        window.location.href = '/dashboard/';
    });

    // Handle user closing tab
    window.addEventListener('beforeunload', () => {
        if (signalingSocket) {
            signalingSocket.send(JSON.stringify({
                'message': { 'type': 'user-left' }
            }));
            signalingSocket.close();
        }
    });

    // Start everything
    startWebRTC();
});
