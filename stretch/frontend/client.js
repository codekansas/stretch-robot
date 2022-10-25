var pc = null;

function negotiate() {
  pc.addTransceiver("video", { direction: "recvonly" });

  return pc
    .createOffer()
    .then(function (offer) {
      return pc.setLocalDescription(offer);
    })
    .then(function () {
      // wait for ICE gathering to complete
      return new Promise(function (resolve) {
        if (pc.iceGatheringState === "complete") {
          resolve();
        } else {
          function checkState() {
            if (pc.iceGatheringState === "complete") {
              pc.removeEventListener("icegatheringstatechange", checkState);
              resolve();
            }
          }
          pc.addEventListener("icegatheringstatechange", checkState);
        }
      });
    })
    .then(function () {
      var offer = pc.localDescription;
      return fetch("/camera/offer", {
        body: JSON.stringify({
          sdp: offer.sdp,
          type: offer.type,
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    })
    .then(function (response) {
      return response.json();
    })
    .then(function (answer) {
      return pc.setRemoteDescription(answer);
    })
    .catch(function (e) {
      console.log(e);
      alert(e);
    });
}

function start() {
  var config = {
    sdpSemantics: "unified-plan",
    iceServers: [{ urls: ["stun:stun.l.google.com:19302"] }],
  };

  pc = new RTCPeerConnection(config);

  // Connect video stream.
  pc.addEventListener("track", function (evt) {
    if (evt.track.kind == "video") {
      document.getElementById("video").srcObject = evt.streams[0];
    }
  });

  document.getElementById("start").disabled = true;
  negotiate();
  document.getElementById("stop").disabled = false;
}

function stop() {
  document.getElementById("stop").disabled = true;

  setTimeout(function () {
    pc.close();
    document.getElementById("start").disabled = false;
  }, 500);
}
