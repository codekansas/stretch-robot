import Button from "react-bootstrap/Button";

const Camera = () => {
  return (
    <>
      <Button id="start" className="m-1">
        Start
      </Button>
      <Button id="stop" className="m-1" disabled>
        Stop
      </Button>

      <div id="media">
        <video
          id="video"
          autoPlay={true}
          playsInline={true}
          className="m-1"
          style={{ border: "1px solid black" }}
        ></video>
      </div>
    </>
  );
};

export default Camera;
