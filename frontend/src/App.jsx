import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home.jsx";
import CmbsQa from "./pages/CmbsQa.jsx";
import IngestFile from "./pages/IngestFile.jsx";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/cmbs-qa" element={<CmbsQa />} />
      <Route path="/ingest-file" element={<IngestFile />} />
    </Routes>
  );
}

export default App;
