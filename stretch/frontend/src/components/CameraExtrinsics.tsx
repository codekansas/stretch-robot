import React from "react";
import Button from "react-bootstrap/Button";
import ButtonGroup from "react-bootstrap/ButtonGroup";
import ButtonToolbar from "react-bootstrap/ButtonToolbar";
import Container from "react-bootstrap/Container";
import Row from "react-bootstrap/Row";

const styles = {
  spinner: {
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

export interface Extrinsics {
  rotation: [
    [number, number, number],
    [number, number, number],
    [number, number, number]
  ];
  translation: [number, number, number];
}

const CameraExtrinsics = () => {
  const [show, setShow] = React.useState<boolean>(false);

  return (
    <Container>
      <Row>
        <h3>Extrinsics</h3>
      </Row>
      <Row>
        <ButtonToolbar className="m-1" style={styles.spinner}>
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
    </Container>
  );
};

export default CameraExtrinsics;
