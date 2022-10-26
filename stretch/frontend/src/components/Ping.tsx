import React from "react";
import { Container } from "react-bootstrap";

const Ping = () => {
  const [ping, setPing] = React.useState<number | null>(null);

  React.useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ping/ws`);

    const interval = setInterval(() => {
      if (ws.OPEN) ws.send(JSON.stringify({ time: Date.now() }));
    }, 1000);

    ws.onmessage = (event) => {
      console.log("Previous time:", JSON.parse(event.data).time);
      console.log("Current time:", Date.now());
      setPing(Date.now() - JSON.parse(event.data).time);
    };

    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, []);

  return (
    <Container className="p-3">
      Ping: {ping === null ? "Connecting..." : `${ping} ms`}
    </Container>
  );
};

export default Ping;
