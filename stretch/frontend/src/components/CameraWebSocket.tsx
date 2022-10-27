import React from "react";
import Button from "react-bootstrap/Button";
import ButtonGroup from "react-bootstrap/ButtonGroup";
import ButtonToolbar from "react-bootstrap/ButtonToolbar";
import Container from "react-bootstrap/Container";
import Row from "react-bootstrap/Row";
import Spinner from "react-bootstrap/Spinner";

const styles = {
  centered: {
    justifyContent: "center",
    display: "flex",
    alignItems: "center",
  },
  image: {
    border: "1px solid black",
    width: "100%",
    aspectRatio: 4 / 3,
  },
};

type CameraType = "depth" | "rgb";

const camera_type_to_name = (c: CameraType) => {
  switch (c) {
    case "depth":
      return "Depth";
    case "rgb":
      return "RGB";
  }
  return "UNKNOWN";
};

export interface Props {
  camera: CameraType;
}

const CameraWebSocket = ({ camera }: Props) => {
  const [show, setShow] = React.useState<boolean>(false);
  const [src, setSrc] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!show) return () => {};

    const ws = new WebSocket(
      `ws://${window.location.host}/camera/ws`
    );

    ws.onmessage = (event) => setSrc(URL.createObjectURL(event.data));

    return () => {
      setSrc(null);
      ws.close();
    };
  }, [show]);

  return (
    <Container>
      <Row>
        <h3>{camera_type_to_name(camera)} Camera</h3>
      </Row>
      <Row>
        <ButtonToolbar className="m-1" style={styles.centered}>
          <ButtonGroup>
            <Button id="start" disabled={show} onClick={() => setShow(true)}>
              Start
            </Button>
            <Button id="stop" disabled={!show} onClick={() => setShow(false)}>
              Stop
            </Button>
          </ButtonGroup>
        </ButtonToolbar>
      </Row>
      {show ? (
        <Row>
          <Container className="m-1">
            {src === null ? (
              <Container style={{ ...styles.image, ...styles.centered }}>
                <Spinner animation="border" role="status">
                  <span className="visually-hidden">Loading...</span>
                </Spinner>
              </Container>
            ) : (
              <img style={styles.image} src={src} alt="Video stream" />
            )}
          </Container>
        </Row>
      ) : null}
    </Container>
  );
};

export default CameraWebSocket;
