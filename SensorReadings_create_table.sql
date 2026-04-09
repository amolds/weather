CREATE TABLE SensorReadings (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    Temperature FLOAT,
    Pressure FLOAT,
    Humidity FLOAT,
    Lux FLOAT,
    Timestamp DATETIME
);

