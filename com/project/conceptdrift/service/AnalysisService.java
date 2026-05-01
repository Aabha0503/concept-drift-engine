package com.project.conceptdrift.service;

import com.project.conceptdrift.dto.AnalysisRequest;
import com.project.conceptdrift.repo.DatasetRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;

@Service
public class AnalysisService {

    private final DatasetRepository datasetRepository;
    private final RestTemplate restTemplate;

    public AnalysisService(DatasetRepository datasetRepository, RestTemplate restTemplate) {
        this.datasetRepository = datasetRepository;
        this.restTemplate=restTemplate;
    }
    // PHASE 2: Will be used when user upload is enabled
//    public String storeDataset(MultipartFile file) throws IOException {
//
//        if (file.isEmpty()) {
//            return "File is empty";
//        }
//
//        Dataset dataset = new Dataset();
//        dataset.setDatasetName(file.getOriginalFilename());
//        dataset.setUploadTime(LocalDateTime.now());
//        dataset.setRawData(new String(file.getBytes()));
//        dataset.setStatus("UPLOADED");
//        datasetRepository.save(dataset);
//
//        return "Dataset stored successfully with ID: " + dataset.getId();
//    }
    // PHASE 1: Used by UI controller with hard-coded path
    public String callPythonAnalysis(String csvPath) {

        String pythonUrl = "http://127.0.0.1:8000/analyze";

        AnalysisRequest request = new AnalysisRequest(csvPath);

        ResponseEntity<String> response =
                restTemplate.postForEntity(pythonUrl, request, String.class);

        return response.getBody();
    }

    public String storeDatasetAndReturnPath(MultipartFile file) throws IOException {

        if (file.isEmpty()) {
            throw new IOException("Uploaded file is empty");
        }

        // ABSOLUTE base directory of Spring Boot project
        String baseDir = System.getProperty("user.dir");

        // Directory for uploads
        Path uploadDir = Paths.get(baseDir, "uploaded-datasets");
        Files.createDirectories(uploadDir);

        // Unique file name
        String fileName = System.currentTimeMillis() + "_" + file.getOriginalFilename();
        Path filePath = uploadDir.resolve(fileName);

        // Save file
        Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);

        // 🔑 RETURN ABSOLUTE PATH
        return filePath.toAbsolutePath().toString();
    }


}