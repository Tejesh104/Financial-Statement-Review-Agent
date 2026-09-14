import React, { createContext, useContext, useEffect, useState } from 'react';
import api from './api';

const DocumentContext = createContext(null);

const emptyDocument = {
  id: null,
  filename: null,
  fileType: null,
  fileSize: null,
  uploadDate: null,
  screeningScore: null,
  verificationStatus: null,
  checks: {},
  details: null,
  findings: [],
  report: null
};

export const DocumentProvider = ({ children }) => {
  const [currentDocument, setCurrentDocumentState] = useState(() => {
    try {
      const saved = sessionStorage.getItem('fsra_current_document');
      return saved ? JSON.parse(saved) : emptyDocument;
    } catch {
      return emptyDocument;
    }
  });
  const [uploadedFileInfo, setUploadedFileInfoState] = useState(() => {
    try {
      const saved = sessionStorage.getItem('fsra_uploaded_file_info');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isHydrating, setIsHydrating] = useState(false);
  const [hydrationError, setHydrationError] = useState('');

  const setCurrentDocument = (doc) => {
    setCurrentDocumentState(doc);
    try {
      if (doc && doc.id) {
        sessionStorage.setItem('fsra_current_document', JSON.stringify(doc));
      } else {
        sessionStorage.removeItem('fsra_current_document');
      }
    } catch (e) {}
  };

  const setUploadedFileInfo = (info) => {
    setUploadedFileInfoState(info);
    try {
      if (info) {
        sessionStorage.setItem('fsra_uploaded_file_info', JSON.stringify(info));
      } else {
        sessionStorage.removeItem('fsra_uploaded_file_info');
      }
    } catch (e) {}
  };

  // Critical Data-State Rule:
  // Fresh sessions start completely empty with zero stale/previous financial data.
  // Documents and analysis results are only populated when the authenticated user
  // explicitly uploads and processes a financial statement in the active session.
  useEffect(() => {
    setIsHydrating(false);
  }, []);

  const setUploadedFile = (file) => {
    const ext = file.name ? file.name.split('.').pop().toUpperCase() : 'CSV';
    const sizeMB = file.size ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : 'Unknown';
    const info = {
      filename: file.name || 'Uploaded_Statement',
      fileType: ext,
      fileSize: sizeMB,
      uploadDate: new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC',
    };
    setUploadedFileInfo(info);
  };

  const resetDocument = () => {
    setCurrentDocumentState(emptyDocument);
    setUploadedFileInfoState(null);
    setUploadProgress(0);
    setIsUploading(false);
    try {
      sessionStorage.removeItem('fsra_current_document');
      sessionStorage.removeItem('fsra_uploaded_file_info');
    } catch (e) {}
  };

  return (
    <DocumentContext.Provider value={{
      currentDocument,
      setCurrentDocument,
      uploadedFileInfo,
      setUploadedFileInfo,
      setUploadedFile,
      uploadProgress,
      setUploadProgress,
      isUploading,
      setIsUploading,
      isHydrating,
      hydrationError,
      resetDocument,
      hasDocument: !!(currentDocument?.id || uploadedFileInfo),
    }}>
      {children}
    </DocumentContext.Provider>
  );
};

export const useDocument = () => useContext(DocumentContext);
