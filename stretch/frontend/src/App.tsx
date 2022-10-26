import Container from "react-bootstrap/Container";
import "./App.css";
import CameraFrames from "./components/CameraFrames";
import CameraWebSocket from "./components/CameraWebSocket";

const App = () => (
  <div className="App">
    <Container className="p-3 mb-3">
      <CameraFrames />
      <CameraWebSocket />
    </Container>
  </div>
);

export default App;
