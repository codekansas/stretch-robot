import Container from "react-bootstrap/Container";
import "./App.css";
import Camera from "./components/Camera";

const App = () => (
  <div className="App">
    <Container className="p-3 mb-3">
      <Camera />
    </Container>
  </div>
);

export default App;
