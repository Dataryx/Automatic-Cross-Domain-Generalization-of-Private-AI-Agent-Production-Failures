import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { OverviewPage } from "./pages/OverviewPage";
import { ReviewsPage } from "./pages/ReviewsPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { AuditPage } from "./pages/AuditPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<OverviewPage />} />
          <Route path="reviews" element={<ReviewsPage />} />
          <Route path="privacy" element={<PrivacyPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
