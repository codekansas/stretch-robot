import React from "react";
import Button from "react-bootstrap/Button";

const CameraFrames = () => {
  const [show, setShow] = React.useState<boolean>(false);

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
      </div>
      <div className="m-1">
        <img src={show ? "/camera/" : ""} alt="Video stream" />
      </div>
    </>
  );
};

export default CameraFrames;
