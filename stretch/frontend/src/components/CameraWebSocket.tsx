import React from "react";
import Button from "react-bootstrap/Button";

const CameraWebSocket = () => {
  const [show, setShow] = React.useState<boolean>(false);
  const [src, setSrc] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!show) return () => {};

    const ws = new WebSocket(`ws://${window.location.host}/camera/video`);

    ws.onmessage = (event) => setSrc(URL.createObjectURL(event.data));

    return () => {
      setSrc(null);
      ws.close();
    };
  }, [show]);

  return (
    <>
      <div>
        <Button
          id="start"
          className="m-1"
          disabled={show}
          onClick={() => setShow(true)}
        >
          Start
        </Button>
        <Button
          id="stop"
          className="m-1"
          disabled={!show}
          onClick={() => setShow(false)}
        >
          Stop
        </Button>
        <div className="m-1">{src == null ? <img /> : <img src={src} />}</div>
      </div>
    </>
  );
};

export default CameraWebSocket;
