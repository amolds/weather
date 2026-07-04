CREATE TABLE SensorReadings (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    Temperature FLOAT,
    Pressure FLOAT,
    Humidity FLOAT,
    Lux FLOAT,
    Timestamp DATETIME
);
GO

CREATE NONCLUSTERED INDEX IDX_SensorReadings_Timestamp ON [dbo].[SensorReadings] (Timestamp)
INCLUDE (Id, Temperature, Pressure, Humidity, Lux);
GO

