import csv
from datetime import datetime

def createUniqueFilename(headers=None):
    """
    Generates a unique filename based on the current timestamp.

    Returns:
        str: A unique filename in the format 'outputLogYYYYMMDD_HHMMSS.csv'.
    """
    timestamp = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    filename = f"./Data/{timestamp}.csv"
    print(f"New CSV file '{filename}' created successfully.")
    if headers:
        with open(filename, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(headers)
    return filename

def writeData(filename, tofData, bnoData, forceData, headers=None):
    data = []
    """
    Creates a new CSV file with a unique filename based on the current timestamp.

    Args:
        data (list of lists): The data to write to the CSV file.
                              Each inner list represents a row.
        headers (list, optional): A list of strings representing the CSV headers.
                                  If provided, it will be written as the first row.
    """
    # Generate a unique filename using the current timestamp
    data.append(forceData[-1]) 
    for i in tofData:
        data.append(i)
    data.append(bnoData)
    with open(filename, 'a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)

        if headers:
            csv_writer.writerow(headers)
        csv_writer.writerow(data)

filename = createUniqueFilename(["Force_lb", "ToF1_deg", "ToF2_deg", "ToF3_deg", "ToF4_deg", "ToF5_deg", "ToF6_deg", "ToF7_deg", "ToF8_deg", "Gyro_Pitch_deg"])
tofData = [1, 10.5, 12.3, 11.0, 9.8, 10.1, 12.0, 11.5]
bnoData = 7.8
forceData = [100, 150, 200]
writeData(filename, tofData, bnoData, forceData)

# You can call this function again in the same script or in subsequent runs
# to create another uniquely named CSV file.
another_data = [
    ["David", 28, "Berlin"],
    ["Eve", 42, "Tokyo"]
]
writeData(filename, tofData, bnoData, forceData)