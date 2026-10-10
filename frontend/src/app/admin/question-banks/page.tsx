"use client";

import { useEffect, useRef, useState } from "react";
import { Trash2, Upload, Plus, FileSpreadsheet, Sparkles, Brain } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDate } from "@/lib/utils";
import { api } from "@/lib/api";

export default function QuestionBanksPage() {
  const [banks, setBanks] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [newBankName, setNewBankName] = useState("");
  const [newBankDesc, setNewBankDesc] = useState("");
  const [newBankRole, setNewBankRole] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  const fileRef = useRef<HTMLInputElement>(null);

  const loadBanks = () => {
    api.listQuestionBanks()
      .then((r) => setBanks(r.items || []))
      .catch(console.error);
  };

  useEffect(loadBanks, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a file to upload.");
      return;
    }
    if (!newBankName.trim()) {
      setError("Please enter a question bank name.");
      return;
    }

    setUploading(true);
    setError("");
    try {
      await api.uploadQuestionBank(selectedFile, newBankName, newBankDesc, newBankRole);
      setNewBankName("");
      setNewBankDesc("");
      setNewBankRole("");
      setSelectedFile(null);
      if (fileRef.current) fileRef.current.value = "";
      setShowUploadForm(false);
      loadBanks();
    } catch (err: any) {
      setError(err.message || "Failed to upload question bank.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this question bank? This will delete all associated questions.")) return;
    try {
      await api.deleteQuestionBank(id);
      setBanks((prev) => prev.filter((b) => b.id !== id));
    } catch (err: any) {
      alert(`Error deleting question bank: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Question Banks</h1>
          <p className="text-sm text-text-muted mt-0.5">
            Manage custom question sets for your assessment rounds.
          </p>
        </div>
        <Button onClick={() => setShowUploadForm((v) => !v)} size="sm">
          {showUploadForm ? "Cancel" : "Upload Bank"}
        </Button>
      </div>

      {/* Upload Form Card */}
      {showUploadForm && (
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-4 w-4 text-brand" />
              Upload Question Bank CSV/Excel
            </CardTitle>
            <CardDescription>
              Provide questions structured in CSV format with columns: text, round_type, difficulty, expected_answer.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUploadSubmit} className="space-y-4">
              {error && (
                <div className="rounded-lg bg-error-light border border-error/20 px-4 py-3">
                  <p className="text-sm text-error font-medium">{error}</p>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">
                  Bank Name <span className="text-error">*</span>
                </label>
                <Input
                  value={newBankName}
                  onChange={(e) => setNewBankName(e.target.value)}
                  placeholder="e.g. Python Backend Developer Questions"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">
                  Description
                </label>
                <Input
                  value={newBankDesc}
                  onChange={(e) => setNewBankDesc(e.target.value)}
                  placeholder="e.g. Assessment questions covering core language, Django, FastAPI"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">
                  Role Tag / Target Role
                </label>
                <Input
                  value={newBankRole}
                  onChange={(e) => setNewBankRole(e.target.value)}
                  placeholder="e.g. Software Engineer"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">
                  Select File <span className="text-error">*</span>
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="file"
                    ref={fileRef}
                    onChange={handleFileChange}
                    accept=".csv,.xlsx,.xls"
                    className="hidden"
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => fileRef.current?.click()}
                    className="gap-2"
                  >
                    <FileSpreadsheet className="h-4 w-4" />
                    {selectedFile ? selectedFile.name : "Choose CSV/Excel..."}
                  </Button>
                  {selectedFile && (
                    <span className="text-xs text-text-muted">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </span>
                  )}
                </div>
              </div>
              <Button type="submit" loading={uploading} className="w-full mt-2">
                Start Upload & Parse
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Grid of Banks */}
      {banks.length === 0 ? (
        <EmptyState
          icon={Brain}
          title="No question banks found"
          description="Upload a CSV or link jobs to auto-generate question sets using AI."
          action={
            <Button onClick={() => setShowUploadForm(true)} size="sm">
              Upload Question Bank
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {banks.map((bank) => (
            <Card key={bank.id} className="flex flex-col hover:border-brand/40 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-base font-semibold leading-snug line-clamp-1">
                      {bank.name}
                    </CardTitle>
                    <CardDescription className="line-clamp-2 mt-1 min-h-[32px]">
                      {bank.description || "No description provided."}
                    </CardDescription>
                  </div>
                  <Badge variant={bank.source === "ai" ? "success" : "default"} className="shrink-0 flex items-center gap-1">
                    {bank.source === "ai" ? (
                      <>
                        <Sparkles className="h-3 w-3" />
                        AI Gen
                      </>
                    ) : (
                      "Upload"
                    )}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-0 flex-1 flex flex-col justify-between gap-4">
                <div className="flex items-center gap-x-4 gap-y-2 flex-wrap text-xs text-text-muted pt-2 border-t border-border">
                  <div>
                    <p className="font-semibold text-text-primary text-sm">
                      {bank.question_count ?? 0}
                    </p>
                    <p className="mt-0.5">Questions</p>
                  </div>
                  {bank.role_tag && (
                    <div>
                      <p className="font-semibold text-text-primary text-sm">
                        {bank.role_tag}
                      </p>
                      <p className="mt-0.5">Role Tag</p>
                    </div>
                  )}
                  <div>
                    <p className="font-semibold text-text-primary text-sm">
                      {bank.created_at ? formatDate(bank.created_at) : "—"}
                    </p>
                    <p className="mt-0.5">Created</p>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 mt-auto">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-error hover:bg-error-light/10 hover:text-error shrink-0"
                    onClick={() => handleDelete(bank.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
