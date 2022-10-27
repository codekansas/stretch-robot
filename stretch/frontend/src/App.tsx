import Col from "react-bootstrap/Col";
import Container from "react-bootstrap/Container";
import Row from "react-bootstrap/Row";
import "./App.css";
import CameraExtrinsics from "./components/CameraExtrinsics";
import CameraFrames from "./components/CameraFrames";
import Ping from "./components/Ping";

const App = () => (
  <div className="App text-center">
    <Container className="p-5 mb-3 mt-3" style={{ border: "1px solid black" }}>
      <h1 className="mb-3">Stretch Robot Teleop</h1>
      <Row>
        <Col>
          <Ping />
        </Col>
      </Row>
      <Row>
        <Col lg={6}>
          <CameraFrames camera="depth" />
        </Col>
        <Col lg={6}>
          <CameraFrames camera="rgb" />
        </Col>
      </Row>
      <Row>
        <CameraExtrinsics />
      </Row>
    </Container>
  </div>
);

export default App;
