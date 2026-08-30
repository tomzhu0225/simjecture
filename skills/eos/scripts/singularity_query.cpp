// Operator-side Singularity-EOS query driver. Compile against an audited
// Singularity-EOS 1.12 source tree; do not run this file inside the sandbox.
//
//   eos-query IdealGas RHO_G_CM3 TEMPERATURE_K GM1 CV OUTPUT.json
//   eos-query IdealElectrons RHO_G_CM3 TEMPERATURE_K ABAR ZBAR OUTPUT.json
//
// Default library units are CGS.

#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

#include <singularity-eos/eos/eos_electrons.hpp>
#include <singularity-eos/eos/eos_ideal.hpp>

namespace {

void write_result(
    const std::string &path,
    const std::string &model,
    double rho,
    double temperature,
    double pressure,
    double energy,
    double cv) {
  std::ofstream output(path);
  output << std::setprecision(17);
  output << "{\n"
         << "  \"schema_version\": \"0.1.0\",\n"
         << "  \"package\": \"singularity-eos\",\n"
         << "  \"model\": \"" << model << "\",\n"
         << "  \"units\": \"cgs\",\n"
         << "  \"density\": " << rho << ",\n"
         << "  \"temperature\": " << temperature << ",\n"
         << "  \"pressure\": " << pressure << ",\n"
         << "  \"specific_internal_energy\": " << energy << ",\n"
         << "  \"specific_heat\": " << cv << "\n"
         << "}\n";
}

}  // namespace

int main(int argc, char **argv) {
  if (argc != 7) {
    std::cerr << "usage:\n"
              << "  " << argv[0]
              << " IdealGas RHO_G_CM3 TEMPERATURE_K GM1 CV OUTPUT.json\n"
              << "  " << argv[0]
              << " IdealElectrons RHO_G_CM3 TEMPERATURE_K ABAR ZBAR OUTPUT.json\n";
    return 2;
  }
  const std::string model = argv[1];
  const double rho = std::strtod(argv[2], nullptr);
  const double temperature = std::strtod(argv[3], nullptr);
  const std::string output_path = argv[6];

  if (model == "IdealGas") {
    const double gm1 = std::strtod(argv[4], nullptr);
    const double cv_in = std::strtod(argv[5], nullptr);
    const singularity::IdealGas eos(gm1, cv_in);
    const double pressure = eos.PressureFromDensityTemperature(rho, temperature);
    const double energy =
        eos.InternalEnergyFromDensityTemperature(rho, temperature);
    const double cv =
        eos.SpecificHeatFromDensityTemperature(rho, temperature);
    write_result(output_path, model, rho, temperature, pressure, energy, cv);
    return 0;
  }
  if (model == "IdealElectrons") {
    const double abar = std::strtod(argv[4], nullptr);
    const double zbar = std::strtod(argv[5], nullptr);
    const singularity::MeanAtomicProperties properties(abar, zbar);
    const singularity::IdealElectrons eos(properties);
    double lambda[1] = {zbar};
    const double pressure =
        eos.PressureFromDensityTemperature(rho, temperature, lambda);
    const double energy =
        eos.InternalEnergyFromDensityTemperature(rho, temperature, lambda);
    const double cv =
        eos.SpecificHeatFromDensityTemperature(rho, temperature, lambda);
    write_result(output_path, model, rho, temperature, pressure, energy, cv);
    return 0;
  }
  std::cerr << "unknown model " << model << "\n";
  return 2;
}
