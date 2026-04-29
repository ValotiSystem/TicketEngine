/**
 * summary:
 *   Top-level route table.
 */
import { Routes, Route, Navigate } from "react-router-dom";
import { LoginPage } from "../pages/LoginPage";
import { TicketsPage } from "../pages/TicketsPage";
import { TicketDetailPage } from "../pages/TicketDetailPage";
import { NewTicketPage } from "../pages/NewTicketPage";
import { AdminPage } from "../pages/AdminPage";
import { ProtectedRoute } from "./ProtectedRoute";
import { Layout } from "../components/Layout";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Navigate to="/tickets" replace />} />
        <Route path="/tickets" element={<TicketsPage />} />
        <Route path="/tickets/new" element={<NewTicketPage />} />
        <Route path="/tickets/:id" element={<TicketDetailPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
