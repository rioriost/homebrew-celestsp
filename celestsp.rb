class Celestsp < Formula
  include Language::Python::Virtualenv

  desc "Celestial TSP is a Python script that calculates the optimal order of celestial bodies for observation based on their coordinates."
  homepage "https://github.com/rioriost/homebrew-celestsp/"
  url ""
  sha256 ""
  license "MIT"

  depends_on "python@3.13"



  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/macocr", "--help"
  end
end
