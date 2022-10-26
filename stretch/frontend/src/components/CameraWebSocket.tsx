import React from "react";
import { Container } from "react-bootstrap";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";

const styles = {
  spinner: {
    justifyContent: "center",
    display: "flex",
    alignItems: "center",
  },
  image: {
    border: "1px solid black",
    height: 480,
    width: 640,
  },
};

const CameraWebSocket = () => {
  const [show, setShow] = React.useState<boolean>(false);
  const [src, setSrc] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!show) return () => {};

    const ws = new WebSocket(`ws://${window.location.host}/camera/ws`);

    ws.onmessage = (event) => setSrc(URL.createObjectURL(event.data));

    return () => {
      setSrc(null);
      ws.close();
    };
  }, [show]);

  return (
    <Container>
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
      {show ? (
        <Container className="m-1">
          {src === null ? (
            <Container style={{ ...styles.image, ...styles.spinner }}>
              <Spinner animation="border" role="status">
                <span className="visually-hidden">Loading...</span>
              </Spinner>
            </Container>
          ) : (
            <img style={styles.image} src={src} alt="Video stream" />
          )}
        </Container>
      ) : null}
    </Container>
  );
};

export default CameraWebSocket;
